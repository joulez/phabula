PRAGMA foreign_keys=ON;

BEGIN TRANSACTION;

CREATE TABLE app (
    id integer PRIMARY KEY,
    ts timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    name text NOT NULL,
    last_access NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE items (
    id integer PRIMARY KEY,
    ts timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator_id integer NOT NULL REFERENCES users(id),
    title text NOT NULL,
    status_hist_id integer NOT NULL REFERENCES status_hist(id),
    content_hist_id integer NOT NULL REFERENCES content_hist(id)
);
CREATE INDEX item_title_idx ON items (title);
CREATE INDEX item_status_hist_idx ON items(status_hist_id);
CREATE INDEX item_content_hist_idx ON items(content_hist_id);

CREATE TABLE user_agents (
    id integer NOT NULL,
    value text NOT NULL
);

CREATE TABLE ips (
    id integer NOT NULL,
    value text NOT NULL
);

CREATE TABLE session_id (
    id integer NOT NULL,
    value text NOT NULL
);

CREATE TABLE access_list (
    id integer NOT NULL,
    ip_id integer NOT NULL REFERENCES ips,
    ua_id integer NOT NULL REFERENCES user_agents,
    session_id integer NOT NULL REFERENCES sessions
);

CREATE TABLE item_access_log (
    id integer PRIMARY KEY,
    ts timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    item_id integer NOT NULL REFERENCES items,
    access_list_id integer NOT NULL REFERENCES access_list
);

CREATE TABLE status_attrs (
    id integer PRIMARY KEY,
    value text NOT NULL
);
INSERT INTO status_attrs(value) VALUES ('created'), ('posted'), ('unposted'),('deleted'), ('edited');

CREATE TABLE status_hist (
    id integer PRIMARY KEY,
    ts timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    item_id integer NOT NULL REFERENCES items(id),
    status_id integer NOT NULL REFERENCES status_attrs(id)
);
CREATE INDEX status_hist_index_id_idx ON status_hist(item_id);


CREATE TABLE section_attrs (
    id integer PRIMARY KEY,
    value text NOT NULL
);
INSERT INTO section_attrs (value) VALUES ('default');


CREATE TABLE permissions (
    id integer PRIMARY KEY,
    value text NOT NULL
);
INSERT INTO permissions (value) VALUES ('read'), ('write'), ('delete');

CREATE TABLE item_perms (
    item_id integer NOT NULL REFERENCES items(id),
    perm_id integer NOT NULL REFERENCES permissions(id),
    group_id integer NOT NULL REFERENCES groups(id)
);
CREATE INDEX item_perms_item_id_idx ON item_perms(item_id);

CREATE TABLE content (
    id integer PRIMARY KEY,
    item_id integer NOT NULL REFERENCES items(id),
    ts timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data text NOT NULL,
    hash text NOT NULL
);
CREATE INDEX item_id_idx ON content (item_id);

CREATE TABLE content_hist (
    id integer PRIMARY KEY,
    ts timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    item_id integer NOT NULL REFERENCES items(id),
    content_id integer NOT NULL REFERENCES content(id)
);

CREATE TABLE content_authors (
    content_id integer NOT NULL REFERENCES content(id),
    user_id integer NOT NULL REFERENCES users(id),
    UNIQUE (content_id, user_id)
);

CREATE TABLE assets (
    id integer PRIMARY KEY,
    name text NOT NULL,
    data bytea NOT NULL,
    media_type text NOT NULL,
    bsize integer NOT NULL
);

CREATE TABLE links (
    id integer PRIMARY KEY,
    ts timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data text NOT NULL
);

CREATE TABLE users (
    id integer NOT NULL PRIMARY KEY,
    map_id integer,
    name text NOT NULL
);
INSERT INTO users (map_id, name) VALUES (777, 'anonymous');

CREATE TABLE group_attrs (
    id integer PRIMARY KEY,
    value text NOT NULL
);

CREATE TABLE group_members (
    id integer PRIMARY KEY,
    group_id integer NOT NULL REFERENCES group_attrs(id),
    user_id integer NOT NULL REFERENCES users(id),
    UNIQUE (group_id, user_id)
);
CREATE INDEX group_members_user_idx ON group_members(user_id);


CREATE TABLE tags (
    id integer NOT NULL PRIMARY KEY,
    value text NOT NULL UNIQUE
);

CREATE TABLE item_tags (
    item_id integer NOT NULL REFERENCES items(id),
    tag_id integer NOT NULL REFERENCES tags(id)
);
CREATE INDEX item_tags_item_id_idx ON item_tags (item_id);
CREATE INDEX item_tags_tag_id_idx ON item_tags (tag_id);

-- VIEWS
CREATE VIEW view_item_list AS 
SELECT i.id as item_id, 
    i.ts as ts, 
    i.title as title,
    u.name as creator,
    sa.value as status,
    (
        SELECT count(ial.item_id) 
        FROM item_access_log ial 
        WHERE ial.item_id = i.id
    ) AS total_hits,
    (
        SELECT count(ial.item_id) 
        FROM item_access_log ial 
        WHERE ial.item_id = i.id 
        GROUP BY ial.access_list_id
    ) AS unique_hits
    FROM items i 
    LEFT JOIN users u ON i.creator_id = u.id
    LEFT JOIN status_hist sh ON i.status_hist_id = sh.id
    LEFT JOIN status_attrs sa ON sa.id = sh.status_id;


CREATE VIEW view_item AS
SELECT i.id, i.ts, i.title FROM items i ORDER BY i.id;

COMMIT;
