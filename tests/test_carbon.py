from grid_intelligence.carbon import weighted_carbon_intensity


def test_all_nuclear_is_zero():
    assert weighted_carbon_intensity({"nuclear": 100.0}) == 0.0


def test_all_coal_is_coal_factor():
    assert weighted_carbon_intensity({"coal": 100.0}) == 1025.0


def test_half_coal_half_nuclear():
    mix = {"coal": 50.0, "nuclear": 50.0}
    assert weighted_carbon_intensity(mix) == 512.5


def test_empty_mix_is_none():
    assert weighted_carbon_intensity({}) is None
