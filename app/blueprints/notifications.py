from flask import Blueprint, jsonify, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select, update

from ..extensions import db
from ..models import Notification

bp = Blueprint("notifications", __name__)

PREVIEW_COUNT = 8
PAGE_COUNT = 50


def unread_count(user_id: int) -> int:
    return db.session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
    )


def _latest(user_id: int, limit: int) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
    )
    return list(db.session.scalars(stmt))


def _link(notification: Notification) -> str:
    return url_for(
        "reader.read", book_id=notification.book_id, chapter=notification.chapter_number
    )


@bp.get("/notifications")
@login_required
def page():
    items = _latest(current_user.id, PAGE_COUNT)
    return render_template("notifications/list.html", items=items, link=_link)


@bp.get("/api/notifications")
@login_required
def summary():
    return jsonify(
        unread=unread_count(current_user.id),
        items=[
            {
                "id": n.id,
                "message": n.message,
                "url": _link(n),
                "read": n.is_read,
                "created": n.created_at.isoformat() + "Z",
            }
            for n in _latest(current_user.id, PREVIEW_COUNT)
        ],
    )


@bp.post("/api/notifications/read")
@login_required
def mark_read():
    db.session.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    db.session.commit()
    return jsonify(unread=0)
