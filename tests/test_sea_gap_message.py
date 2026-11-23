import graphhopper_enhanced as gh


def test_sea_gap_message():
    data = {"message": "Connection between locations not found"}
    assert gh.routing_error_message(400, data) == gh.SEA_GAP_MESSAGE


def test_unknown_error_keeps_text():
    assert gh.routing_error_message(400, {"message": "Odd"}) == "Routing error 400: Odd"
