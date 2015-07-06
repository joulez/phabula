VIEW_LIST = """
SELECT 
    item_id, 
    ts, 
    title, 
    status,
    creator,
    total_hits,
    unique_hits
    FROM view_item_list;
"""
GET_STATUS_ATTRS = """
SELECT NULL
"""

VIEW_ITEM = """
SELECT * FROM view_item;
"""

# vim:set sw=4 sts=4 ts=4 et tw=79:
