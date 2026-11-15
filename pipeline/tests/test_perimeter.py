from datetime import date, timedelta

import numpy as np
import pytest

from sarstory.nisar.perimeter import analyze_perimeter, diff_in_diff, gaps, ring

H, W = 220, 260
DAYS = [date(2026, 6, 19) + timedelta(days=12 * i) for i in range(8)]  # Jun 19 .. Sep 11
STARTED, MAPPED = date(2026, 8, 2), date(2026, 8, 21)


def scene(drop_db: float, *, wet_shift: float = 1.5, noise: float = 1.2, seed: int = 4):
    """Forest at about -13 dB HV with speckle. On one date the whole scene gets wetter (a regional shift that
    must cancel), and after the fire the pixels inside a blob fall by `drop_db`."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W]
    inside = ((yy - 110) / 18.0) ** 2 + ((xx - 120) / 26.0) ** 2 < 1
    hv = np.empty((len(DAYS), H, W), np.float32)
    for i, d in enumerate(DAYS):
        hv[i] = -13 + rng.normal(0, noise, (H, W))
        if d == date(2026, 8, 30):
            hv[i] += wet_shift
        if d > MAPPED:
            hv[i][inside] -= drop_db
    return hv, inside


def test_ring_is_a_band_around_the_shape_with_a_gap():
    _, inside = scene(0.0)
    around = ring(inside)
    assert not (around & inside).any()
    assert around.sum() > inside.sum()


def test_gap_and_diff_in_diff_recover_a_drop_that_one_pixel_cannot_see():
    hv, inside = scene(0.8)
    g = gaps(hv, inside, ring(inside))
    pre = [i for i, d in enumerate(DAYS) if d < STARTED]
    post = [i for i, d in enumerate(DAYS) if d > MAPPED]
    assert diff_in_diff(g, pre, post) == pytest.approx(-0.8, abs=0.15)


def test_analysis_separates_a_real_drop_from_its_placebos():
    hv, inside = scene(0.8)
    a = analyze_perimeter(
        DAYS, hv, inside, started=STARTED, mapped=MAPPED, min_before_db=-16, pixel_area_m2=3600, placebo_n=60
    )
    assert a.drop_db == pytest.approx(0.8, abs=0.15)
    assert abs(a.stats["placebo_mean_db"]) < 0.15 and a.stats["placebo_sd_db"] < 0.2
    assert a.stats["placebo_share_as_low"] == 0.0
    assert a.pre_days == [d for d in DAYS if d < STARTED] and a.post_days == [d for d in DAYS if d > MAPPED]
    assert a.stats["inside_ha"] == pytest.approx(inside.sum() * 0.36)


def test_no_drop_gives_a_result_inside_the_placebo_spread():
    hv, inside = scene(0.0, seed=9)
    a = analyze_perimeter(
        DAYS, hv, inside, started=STARTED, mapped=MAPPED, min_before_db=-16, pixel_area_m2=3600, placebo_n=60
    )
    assert abs(a.drop_db) < 3 * a.stats["placebo_sd_db"] + 0.05
    assert a.stats["placebo_share_as_low"] > 0.01


def test_a_regional_wet_date_does_not_count_as_a_drop():
    hv, inside = scene(0.0, wet_shift=4.0, seed=11)
    g = gaps(hv, inside, ring(inside))
    assert np.ptp(g) < 0.3  # the shift moves inside and ring together


def test_needs_dates_on_both_sides_and_a_real_shape():
    hv, inside = scene(0.8)
    with pytest.raises(ValueError, match="two dates"):
        analyze_perimeter(
            DAYS, hv, inside, started=DAYS[1], mapped=MAPPED, min_before_db=-16, pixel_area_m2=3600
        )
    with pytest.raises(ValueError, match="fewer than 50"):
        analyze_perimeter(
            DAYS,
            hv,
            np.zeros_like(inside),
            started=STARTED,
            mapped=MAPPED,
            min_before_db=-16,
            pixel_area_m2=3600,
        )


def test_equal_area_square_has_the_cited_area():
    from rasterio.warp import transform_geom
    from shapely.geometry import shape

    from sarstory.nisar.build_imagery import equal_area_square

    utm = transform_geom("EPSG:4326", "EPSG:32749", equal_area_square([110.575, -6.9], 2534.0))
    assert shape(utm).area / 1e4 == pytest.approx(2534.0, rel=0.01)
