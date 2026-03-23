def enforce_user_filter(query, model, user_id, field_name="user_id"):
    return query.filter(getattr(model, field_name) == user_id)