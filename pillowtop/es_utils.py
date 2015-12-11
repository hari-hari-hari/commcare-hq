
INDEX_REINDEX_SETTINGS = {
    "index": {
        "refresh_interval": "900s",
        "merge.policy.merge_factor": 20,
        "store.throttle.max_bytes_per_sec": "1mb",
        "store.throttle.type": "merge",
        "number_of_replicas": "0"
    }
}

INDEX_STANDARD_SETTINGS = {
    "index": {
        "refresh_interval": "1s",
        "merge.policy.merge_factor": 10,
        "store.throttle.max_bytes_per_sec": "5mb",
        "store.throttle.type": "node",
        "number_of_replicas": "0"
    }
}


def update_settings(es, index, settings_dict):
    return es.indices.put_settings(settings_dict, index=index)


def set_index_reindex_settings(es, index):
    """
    Set a more optimized setting setup for fast reindexing
    """
    return update_settings(es, index, INDEX_REINDEX_SETTINGS)


def set_index_normal_settings(es, index):
    """
    Normal indexing configuration
    """
    return update_settings(es, index, INDEX_STANDARD_SETTINGS)


def create_index_and_set_settings_normal(es, index, metadata=None):
    metadata = metadata or {}
    es.indices.create(index=index, body=metadata)
    set_index_normal_settings(es, index)


def pillow_index_exists(pillow):
    return pillow.get_es_new().indices.exists(pillow.es_index)


def create_index_for_pillow(pillow):
    return create_index_and_set_settings_normal(pillow.get_es_new(), pillow.es_index, pillow.es_meta)


def assume_alias_for_pillow(pillow):
    """
    Assigns the pillow's `es_alias` to its index in elasticsearch.

    This operation removes the alias from any other indices it might be assigned to
    """
    es_new = pillow.get_es_new()
    if es_new.indices.exists_alias(pillow.es_alias):
        # this part removes the conflicting aliases
        alias_indices = es_new.indices.get_alias(pillow.es_alias).keys()
        for aliased_index in alias_indices:
            es_new.indices.delete_alias(aliased_index, pillow.es_alias)

    es_new.indices.put_alias(pillow.es_index, pillow.es_alias)
