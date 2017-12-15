import pytest
import datetime
import json

from model_mommy import mommy
from rest_framework import status

from talentmap_api.bidding.models import BidCycle, Bid


@pytest.fixture
def test_bidlist_fixture():
    bidcycle = mommy.make(BidCycle, id=1, name="Bidcycle 1", active=True)
    for i in range(5):
        bidcycle.positions.add(mommy.make('position.Position'))


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("test_bidlist_fixture")
def test_bid_bidder_actions(authorized_client, authorized_user):
    in_cycle_position = BidCycle.objects.first().positions.first()

    # Put the position into the bidlist
    response = authorized_client.put(f'/api/v1/bidlist/position/{in_cycle_position.id}/')

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Get our bidlist, and validate that the position is in the list as a draft
    response = authorized_client.get(f'/api/v1/bidlist/')

    assert response.status_code == status.HTTP_200_OK

    bid = Bid.objects.get(id=response.data["results"][0]["id"])
    assert bid.status == Bid.Status.draft
    assert bid.position.id == in_cycle_position.id
    assert bid.draft_date == datetime.datetime.now().date()
    assert bid.submitted_date is None

    # Submit our bid
    response = authorized_client.get(f'/api/v1/bid/{bid.id}/submit/')

    assert response.status_code == status.HTTP_204_NO_CONTENT

    bid.refresh_from_db()
    assert bid.status == Bid.Status.submitted
    assert bid.draft_date == datetime.datetime.now().date()
    assert bid.submitted_date == datetime.datetime.now().date()

    # Try to submit again, we should get a 404 error since you can't submit a bid that's been submitted
    response = authorized_client.get(f'/api/v1/bid/{bid.id}/submit/')
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Try to accept a handshake on the position. We should get a 404 since there are no matching bids with handshake offered
    response = authorized_client.get(f'/api/v1/bid/{bid.id}/accept_handshake/')
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Update the bid in the DB to have offered a handshake
    bid.status = bid.Status.handshake_offered
    bid.save()

    # Try to accept a handshake on the position.
    response = authorized_client.get(f'/api/v1/bid/{bid.id}/accept_handshake/')
    assert response.status_code == status.HTTP_204_NO_CONTENT

    bid.refresh_from_db()
    assert bid.status == Bid.Status.handshake_accepted
    assert bid.draft_date == datetime.datetime.now().date()
    assert bid.submitted_date == datetime.datetime.now().date()
    assert bid.handshake_accepted_date == datetime.datetime.now().date()


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("test_bidlist_fixture")
def test_bid_ao_actions(authorized_client, authorized_user):
    bidcycle = BidCycle.objects.get(id=1)
    bureau = mommy.make('organization.Organization', code='12345')

    in_bureau_position = mommy.make('position.Position', bureau=bureau)
    out_of_bureau_position = mommy.make('position.Position', bureau=mommy.make('organization.Organization', code='asdfasd'))

    bidcycle.positions.add(in_bureau_position)
    bidcycle.positions.add(out_of_bureau_position)

    in_bureau_bid = mommy.make(Bid, user=mommy.make('auth.User').profile, position=in_bureau_position, bidcycle=bidcycle, status=Bid.Status.draft)
    out_of_bureau_bid = mommy.make(Bid, user=mommy.make('auth.User').profile, position=out_of_bureau_position, bidcycle=bidcycle, status=Bid.Status.submitted)

    # Give our user appropriate permissions
    group = mommy.make('auth.Group', name='bureau_ao')
    group.user_set.add(authorized_user)
    group = mommy.make('auth.Group', name=f'bureau_ao_{bureau.code}')
    group.user_set.add(authorized_user)

    # Offer a handshake, this should 404 since there's no matching bid (because it lacks the submitted status)
    response = authorized_client.get(f'/api/v1/bid/{in_bureau_bid.id}/offer_handshake/')
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Submit the bid
    in_bureau_bid.status = Bid.Status.submitted
    in_bureau_bid.save()

    # Offer handshake
    response = authorized_client.get(f'/api/v1/bid/{in_bureau_bid.id}/offer_handshake/')
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Try to offer for a bid for a handshake the user is not an AO for
    response = authorized_client.get(f'/api/v1/bid/{out_of_bureau_bid.id}/offer_handshake/')
    assert response.status_code == status.HTTP_403_FORBIDDEN

    in_bureau_bid.refresh_from_db()
    assert in_bureau_bid.status == Bid.Status.handshake_offered
    assert in_bureau_bid.handshake_offered_date == datetime.datetime.now().date()

    # Accept the handshakes
    in_bureau_bid.status = Bid.Status.handshake_accepted
    in_bureau_bid.save()
    out_of_bureau_bid.status = Bid.Status.handshake_accepted
    out_of_bureau_bid.save()

    # Set the panel date
    response = authorized_client.patch(f'/api/v1/bid/{in_bureau_bid.id}/schedule_panel/', data=json.dumps({
        "scheduled_panel_date": "2019-01-01"
    }), content_type="application/json")

    assert response.status_code == status.HTTP_200_OK

    in_bureau_bid.refresh_from_db()
    assert in_bureau_bid.status == Bid.Status.in_panel
    assert in_bureau_bid.in_panel_date == datetime.datetime.now().date()
    assert str(in_bureau_bid.scheduled_panel_date) == "2019-01-01"

    # Patch an out-of-bureau bid
    response = authorized_client.patch(f'/api/v1/bid/{out_of_bureau_bid.id}/schedule_panel/', data=json.dumps({
        "scheduled_panel_date": "2019-01-01"
    }), content_type="application/json")

    assert response.status_code == status.HTTP_403_FORBIDDEN

    out_of_bureau_bid.status = Bid.Status.in_panel
    out_of_bureau_bid.save()

    # Approve the bid
    response = authorized_client.get(f'/api/v1/bid/{in_bureau_bid.id}/approve/')
    assert response.status_code == status.HTTP_204_NO_CONTENT

    in_bureau_bid.refresh_from_db()
    assert in_bureau_bid.status == Bid.Status.approved
    assert in_bureau_bid.approved_date == datetime.datetime.now().date()

    response = authorized_client.get(f'/api/v1/bid/{out_of_bureau_bid.id}/approve/')
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Decline the bid
    response = authorized_client.get(f'/api/v1/bid/{in_bureau_bid.id}/decline/')
    assert response.status_code == status.HTTP_204_NO_CONTENT

    in_bureau_bid.refresh_from_db()
    assert in_bureau_bid.status == Bid.Status.declined
    assert in_bureau_bid.declined_date == datetime.datetime.now().date()

    response = authorized_client.get(f'/api/v1/bid/{out_of_bureau_bid.id}/decline/')
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("test_bidlist_fixture")
def test_bidlist_max_submissions(authorized_client, authorized_user):
    bidcycle = BidCycle.objects.get(id=1)
    position = mommy.make('position.Position')
    bidcycle.positions.add(position)
    mommy.make(Bid, user=authorized_user.profile, bidcycle=bidcycle, status=Bid.Status.submitted, position=position, _quantity=10)

    bid = mommy.make(Bid, user=authorized_user.profile, bidcycle=bidcycle, status=Bid.Status.draft, position=position)

    # Submit our bid - this should fail as we will exceed the amount of allowable submissions!
    response = authorized_client.get(f'/api/v1/bid/{bid.id}/submit/')

    assert response.status_code == status.HTTP_400_BAD_REQUEST