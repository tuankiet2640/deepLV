"""Metrics endpoint: path-param cardinality collapse + unmatched-route bucketing."""

import pytest


@pytest.mark.asyncio
async def test_path_params_collapse_into_one_label(client):
    # Unauthenticated is fine -- route matching (and so metrics templating)
    # happens before auth dependencies run, regardless of the resulting status.
    r1 = await client.get("/api/v1/documents/jobs/11111111-1111-1111-1111-111111111111")
    r2 = await client.get("/api/v1/documents/jobs/22222222-2222-2222-2222-222222222222")
    if r1.status_code == 500 or r2.status_code == 500:
        pytest.skip("PostgreSQL not available")

    metrics = await client.get("/metrics")
    text = metrics.text

    assert 'endpoint="/api/v1/documents/jobs/{job_id}"' in text
    # Neither raw UUID should ever appear as a label value -- that's the leak/
    # cardinality-explosion this test guards against.
    assert "11111111-1111-1111-1111-111111111111" not in text
    assert "22222222-2222-2222-2222-222222222222" not in text


@pytest.mark.asyncio
async def test_unmatched_routes_collapse_into_single_bucket(client):
    r1 = await client.get("/api/v1/this/route/does/not/exist/abc")
    r2 = await client.get("/api/v1/this/route/does/not/exist/xyz")
    if r1.status_code == 500 or r2.status_code == 500:
        pytest.skip("PostgreSQL not available")
    assert r1.status_code == 404
    assert r2.status_code == 404

    metrics = await client.get("/metrics")
    text = metrics.text

    assert 'endpoint="{unmatched}"' in text
    assert "does/not/exist/abc" not in text
    assert "does/not/exist/xyz" not in text
