# Copyright (C) 2010-2013 Yaco Sistemas (http://www.yaco.es)
# Copyright (C) 2009 Lorenzo Gil Sanchez <lorenzo.gil.sanchez@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#            http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''
Monkeypatch for consumer service to provide redirect url with user's expiring token
'''
import logging

try:
    from xml.etree import ElementTree
except ImportError:
    from elementtree import ElementTree

from django.conf import settings
from django.contrib import auth
try:
    from django.contrib.auth.views import LogoutView
    django_logout = LogoutView.as_view()
except ImportError:
    from django.contrib.auth.views import logout as django_logout
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from saml2 import BINDING_HTTP_POST
from saml2.sigver import MissingKey
from saml2.response import (
    StatusError, StatusAuthnFailed, SignatureError, StatusRequestDenied,
    UnsolicitedResponse,
)
from saml2.validate import ResponseLifetimeExceed, ToEarly

from djangosaml2.cache import IdentityCache, OutstandingQueriesCache
from djangosaml2.conf import get_config
from djangosaml2.overrides import Saml2Client
from djangosaml2.signals import post_authenticated
from djangosaml2.utils import (
    fail_acs_response, get_custom_setting, is_safe_url_compat,
)

from djangosaml2.views import _set_subject_id
from rest_framework_expiring_authtoken.models import ExpiringToken

logger = logging.getLogger('console')


@require_POST
@csrf_exempt
def assertion_consumer_service(request,
                               config_loader_path=None,
                               attribute_mapping=None,
                               create_unknown_user=None):
    """SAML Authorization Response endpoint
    The IdP will send its response to this view, which
    will process it with pysaml2 help and log the user
    in using the custom Authorization backend
    djangosaml2.backends.Saml2Backend that should be
    enabled in the settings.py
    """
    attribute_mapping = attribute_mapping or get_custom_setting('SAML_ATTRIBUTE_MAPPING', {'uid': ('username', )})
    create_unknown_user = create_unknown_user if create_unknown_user is not None else \
                          get_custom_setting('SAML_CREATE_UNKNOWN_USER', True)
    conf = get_config(config_loader_path, request)
    try:
        xmlstr = request.POST['SAMLResponse']
    except KeyError:
        logger.warning('Missing "SAMLResponse" parameter in POST data.')
        raise SuspiciousOperation

    client = Saml2Client(conf, identity_cache=IdentityCache(request.session))

    oq_cache = OutstandingQueriesCache(request.session)
    outstanding_queries = oq_cache.outstanding_queries()

    try:
        response = client.parse_authn_request_response(xmlstr, BINDING_HTTP_POST, outstanding_queries)
    except (StatusError, ToEarly):
        logger.exception("Error processing SAML Assertion.")
        return fail_acs_response(request)
    except ResponseLifetimeExceed:
        logger.info("SAML Assertion is no longer valid. Possibly caused by network delay or replay attack.", exc_info=True)
        return fail_acs_response(request)
    except SignatureError:
        logger.info("Invalid or malformed SAML Assertion.", exc_info=True)
        return fail_acs_response(request)
    except StatusAuthnFailed:
        logger.info("Authentication denied for user by IdP.", exc_info=True)
        return fail_acs_response(request)
    except StatusRequestDenied:
        logger.warning("Authentication interrupted at IdP.", exc_info=True)
        return fail_acs_response(request)
    except MissingKey:
        logger.exception("SAML Identity Provider is not configured correctly: certificate key is missing!")
        return fail_acs_response(request)
    except UnsolicitedResponse:
        logger.exception("Received SAMLResponse when no request has been made.")
        return fail_acs_response(request)

    if response is None:
        logger.warning("Invalid SAML Assertion received (unknown error).")
        return fail_acs_response(request, status=400, exc_class=SuspiciousOperation)

    session_id = response.session_id()
    oq_cache.delete(session_id)

    # authenticate the remote user
    session_info = response.session_info()

    if callable(attribute_mapping):
        attribute_mapping = attribute_mapping()
    if callable(create_unknown_user):
        create_unknown_user = create_unknown_user()

    logger.debug('Trying to authenticate the user. Session info: %s', session_info)
    user = auth.authenticate(request=request,
                             session_info=session_info,
                             attribute_mapping=attribute_mapping,
                             create_unknown_user=create_unknown_user)
    if user is None:
        logger.warning("Could not authenticate user received in SAML Assertion. Session info: %s", session_info)
        raise PermissionDenied

    auth.login(request, user)
    _set_subject_id(request.session, session_info['name_id'])
    logger.debug("User %s authenticated via SSO.", user)

    logger.debug('Sending the post_authenticated signal')
    post_authenticated.send_robust(sender=user, session_info=session_info)

    # Get user's token
    token, _ = ExpiringToken.objects.get_or_create(user=user)
    if token and token.is_expired():
        token.delete()
        token = ExpiringToken.objects.create(user=user)

    token_redirect_url = f"{settings.LOGIN_REDIRECT_URL}?tmApiToken={token.key}"

    # redirect the user to the view where he came from
    default_relay_state = get_custom_setting('ACS_DEFAULT_REDIRECT_URL',
                                             token_redirect_url)
    relay_state = request.POST.get('RelayState', default_relay_state)
    if not relay_state:
        logger.warning('The RelayState parameter exists but is empty')
        relay_state = default_relay_state
    if not is_safe_url_compat(url=relay_state, allowed_hosts={request.get_host()}):
        relay_state = token_redirect_url
    logger.debug('Redirecting to the RelayState: %s', relay_state)
    return HttpResponseRedirect(relay_state)
