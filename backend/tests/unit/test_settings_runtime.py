from agentic_crag.config import Settings


def test_active_helpers_local_defaults() -> None:
    s = Settings(
        local_dev_mode=True,
        free_models_only=False,  # avoid model assert side effects if keys absent
    )
    assert s.active_embedding_dims == 384
    assert s.active_qdrant_collection == "crag_chunks_local"


def test_active_helpers_cloud() -> None:
    s = Settings(
        local_dev_mode=False,
        embedding_dims=768,
        qdrant_collection="crag_chunks",
        free_models_only=False,
    )
    assert s.active_embedding_dims == 768
    assert s.active_qdrant_collection == "crag_chunks"
