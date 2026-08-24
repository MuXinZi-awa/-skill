from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from signer_base import Signer


@dataclass
class CommentResponse:
    ok: bool
    status: str
    msg: str
    comment_id: int | None
    floor: int | None
    http_status_code: int
    response_text_preview: str
    raw: dict[str, Any]


@dataclass
class PostContentResponse:
    ok: bool
    status: str
    msg: str
    link_content: str
    comments: list[dict[str, Any]]
    raw: dict[str, Any]


@dataclass
class FeedIdsResponse:
    ok: bool
    status: str
    msg: str
    items: list[dict[str, Any]]
    raw: dict[str, Any]


class HeyboxCommentClient:
    def __init__(
        self,
        *,
        base_url: str,
        req_path: str,
        default_query: dict[str, Any],
        headers: dict[str, str],
        cookie: str,
        signer: Signer,
        timeout_seconds: int = 15,
    ) -> None:
        self.base_url = base_url
        self.req_path = req_path
        self.default_query = default_query
        self.headers = dict(headers)
        self.headers["Cookie"] = cookie
        self.signer = signer
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.trust_env = False

    def update_runtime(
        self,
        *,
        base_url: str | None = None,
        req_path: str | None = None,
        default_query: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        cookie: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        if base_url is not None:
            self.base_url = base_url
        if req_path is not None:
            self.req_path = req_path
        if default_query is not None:
            self.default_query = dict(default_query)
        if headers is not None:
            self.headers = dict(headers)
            if cookie is not None:
                self.headers["Cookie"] = cookie
        elif cookie is not None:
            self.headers["Cookie"] = cookie
        if timeout_seconds is not None:
            self.timeout_seconds = timeout_seconds

    @staticmethod
    def _extract_link_content(data: dict[str, Any]) -> str:
        result = data.get("result", {})
        if not isinstance(result, dict):
            return ""
        link = result.get("link", {})
        if not isinstance(link, dict):
            return ""
        for key in ("content", "text", "description", "desc"):
            value = link.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    @staticmethod
    def _extract_comments(data: dict[str, Any]) -> list[dict[str, Any]]:
        comments: list[dict[str, Any]] = []
        seen_ids: set[int] = set()

        result = data.get("result", {})
        if not isinstance(result, dict):
            return comments

        def walk(node: Any) -> None:
            if isinstance(node, list):
                for item in node:
                    walk(item)
                return
            if not isinstance(node, dict):
                return

            # Match actual comment item shape: has commentid + text.
            if "commentid" in node:
                cid_raw = node.get("commentid")
                if isinstance(cid_raw, int) and cid_raw not in seen_ids:
                    text_val = node.get("text")
                    text_clean = text_val.strip() if isinstance(text_val, str) else ""
                    user_obj = node.get("user") if isinstance(node.get("user"), dict) else {}
                    comments.append(
                        {
                            "comment_id": cid_raw,
                            "text": text_clean,
                            "user_id": user_obj.get("userid", node.get("userid")),
                            "username": user_obj.get("username"),
                            "create_at": node.get("create_at"),
                            "ip_location": node.get("ip_location"),
                            "floor_num": node.get("floor_num"),
                            "reply_id": node.get("reply_id"),
                            "root_id": node.get("root_id"),
                            "parent_comment_id": node.get("reply_id"),
                            "reply_user_id": node.get("reply_userid", node.get("to_userid")),
                            "reply_username": node.get("reply_username", node.get("to_username")),
                            "is_link_owner": node.get("is_link_owner"),
                            "child_num": node.get("child_num"),
                        }
                    )
                    seen_ids.add(cid_raw)

            for value in node.values():
                walk(value)

        walk(result)
        return comments

    def create_comment(
        self,
        *,
        link_id: int,
        text: str,
        is_cy: int = 0,
        reply_id: int = -1,
        root_id: int = -1,
    ) -> CommentResponse:
        if not text.strip():
            raise ValueError("text cannot be empty")

        keys = self.signer.get_keys(self.req_path)

        params = dict(self.default_query)
        params.update({
            "hkey": keys.hkey,
            "nonce": keys.nonce,
            "_time": str(keys.Rtime),
        })

        body = {
            "is_cy": str(is_cy),
            "link_id": str(link_id),
            "reply_id": str(reply_id),
            "root_id": str(root_id),
            "text": text,
        }

        resp = self.session.post(
            self.base_url,
            params=params,
            data=body,
            headers=self.headers,
            timeout=self.timeout_seconds,
        )
        http_status = resp.status_code
        resp_text = resp.text
        resp.raise_for_status()
        data = resp.json()
        status = str(data.get("status", ""))
        msg = str(data.get("msg", ""))
        comment_id = data.get("commentid")
        floor = data.get("floor")

        return CommentResponse(
            ok=status == "ok",
            status=status,
            msg=msg,
            comment_id=int(comment_id) if isinstance(comment_id, int) else None,
            floor=int(floor) if isinstance(floor, int) else None,
            http_status_code=http_status,
            response_text_preview=resp_text[:500],
            raw=data,
        )

    def fetch_post_content(
        self,
        *,
        link_id: int,
        tree_path: str = "/bbs/app/link/tree",
        tree_url: str = "https://api.xiaoheihe.cn/bbs/app/link/tree",
        is_first: int = 1,
        page: int = 1,
        index: int = 1,
        limit: int = 20,
        owner_only: int = 0,
        h_src: str = "",
    ) -> PostContentResponse:
        keys = self.signer.get_keys(tree_path)
        params = dict(self.default_query)
        params.update(
            {
                "hkey": keys.hkey,
                "nonce": keys.nonce,
                "_time": str(keys.Rtime),
                "link_id": str(link_id),
                "is_first": str(is_first),
                "page": str(page),
                "index": str(index),
                "limit": str(limit),
                "owner_only": str(owner_only),
                "h_src": h_src,
            }
        )

        resp = self.session.get(
            tree_url,
            params=params,
            headers=self.headers,
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()

        data = resp.json()
        status = str(data.get("status", ""))
        msg = str(data.get("msg", ""))
        link_content = self._extract_link_content(data)
        comments = self._extract_comments(data)

        return PostContentResponse(
            ok=status == "ok",
            status=status,
            msg=msg,
            link_content=link_content,
            comments=comments,
            raw=data,
        )

    @staticmethod
    def _extract_feed_items(data: dict[str, Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        seen: set[int] = set()

        def normalize_link_id(v: Any) -> int | None:
            if isinstance(v, int):
                return v
            if isinstance(v, str) and v.isdigit():
                return int(v)
            return None

        def walk(node: Any) -> None:
            if isinstance(node, list):
                for item in node:
                    walk(item)
                return
            if not isinstance(node, dict):
                return

            link_id = None
            for k in ("link_id", "linkid", "linkId"):
                link_id = normalize_link_id(node.get(k))
                if link_id is not None:
                    break

            if link_id is not None and link_id not in seen:
                title = ""
                for tk in ("title", "name", "subject"):
                    tv = node.get(tk)
                    if isinstance(tv, str) and tv.strip():
                        title = tv.strip()
                        break
                topics_raw = node.get("topics")
                topics: list[dict[str, Any]] = []
                if isinstance(topics_raw, list):
                    for topic in topics_raw:
                        if isinstance(topic, dict):
                            topics.append(topic)
                items.append(
                    {
                        "link_id": link_id,
                        "title": title,
                        "create_at": node.get("create_at"),
                        "userid": node.get("userid"),
                        "topics": topics,
                    }
                )
                seen.add(link_id)

            for value in node.values():
                walk(value)

        walk(data.get("result", data))
        return items

    @staticmethod
    def _item_matches_topic(item: dict[str, Any], topic_id: int | None) -> bool:
        if not isinstance(topic_id, int) or topic_id <= 0:
            return True
        topics = item.get("topics")
        if not isinstance(topics, list):
            return False
        for topic in topics:
            if not isinstance(topic, dict):
                continue
            tid = topic.get("topic_id")
            if isinstance(tid, int) and tid == topic_id:
                return True
            if isinstance(tid, str) and tid.isdigit() and int(tid) == topic_id:
                return True
        return False

    def fetch_feed_ids(
        self,
        *,
        feeds_path: str = "/bbs/app/feeds",
        feeds_url: str = "https://api.xiaoheihe.cn/bbs/app/feeds",
        pull: int = 0,
        offset: int = 0,
        dw: int = 604,
        limit: int = 10,
        topic_id: int | None = None,
        lastval: bool = False,
        min_create_at: int | None = None,
        extra_query: dict[str, Any] | None = None,
    ) -> FeedIdsResponse:
        keys = self.signer.get_keys(feeds_path)
        params = dict(self.default_query)
        params.update(
            {
                "pull": str(pull),
                "offset": str(offset),
                "dw": str(dw),
                "limit": str(limit),
                "hkey": keys.hkey,
                "_time": str(keys.Rtime),
                "nonce": keys.nonce,
            }
        )
        if isinstance(topic_id, int) and topic_id > 0:
            params["topic_id"] = str(topic_id)
        if lastval:
            params["lastval"] = ""
        if extra_query:
            params.update({k: str(v) for k, v in extra_query.items()})

        resp = self.session.get(
            feeds_url,
            params=params,
            headers=self.headers,
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        data = resp.json()
        status = str(data.get("status", ""))
        msg = str(data.get("msg", ""))
        items = self._extract_feed_items(data)
        if isinstance(topic_id, int) and topic_id > 0:
            items = [it for it in items if self._item_matches_topic(it, topic_id)]
        if isinstance(min_create_at, int) and min_create_at > 0:
            filtered: list[dict[str, Any]] = []
            for it in items:
                ts = it.get("create_at")
                ts_int: int | None = None
                if isinstance(ts, int):
                    ts_int = ts
                elif isinstance(ts, str) and ts.isdigit():
                    ts_int = int(ts)
                if ts_int is not None and ts_int >= min_create_at:
                    filtered.append(it)
            items = filtered
        return FeedIdsResponse(ok=status == "ok", status=status, msg=msg, items=items, raw=data)
