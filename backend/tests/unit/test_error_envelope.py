"""Behaviour: build_error_body splits user_message vs developer_message.

Module: agentic_crag.api.error_envelope. Existing tests: none for this module.
User: "backend should also give meaning full errors msg to frontend and errors
for developers".
"""

from __future__ import annotations

from agentic_crag.api.error_envelope import build_error_body, user_message_for


def test_user_message_catalog() -> None:
    assert "ready" in user_message_for("ERR_GRAPH_NOT_READY").lower()


def test_build_exposes_developer() -> None:
    body = build_error_body(
        code="ERR_GRAPH_STREAM",
        developer_message="ValueError: boom",
        expose_developer=True,
        correlation_id="cid-1",
    )
    assert body.user_message
    assert "ValueError" in body.developer_message
    assert "cid-1" in body.developer_message
    assert body.message == body.user_message
    assert body.layer == "backend"


def test_build_redacts_developer() -> None:
    body = build_error_body(
        code="ERR_INTERNAL",
        developer_message="secret stack",
        expose_developer=False,
        correlation_id="cid-2",
    )
    assert "secret stack" not in body.developer_message
    assert "cid-2" in body.developer_message
