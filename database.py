import sqlite3
from dataclasses import dataclass
from typing import Optional


@dataclass
class Tag:
    id: int
    name: str
    channel: str
    scene: Optional[str] = None
    npc: Optional[str] = None
    level: Optional[int] = None


class Database:
    """SQLite database for bot state."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER NOT NULL PRIMARY KEY,
                    name TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    scene TEXT,
                    npc TEXT,
                    level INTEGER
                )
            """)
            conn.commit()

    def create_tag(
        self,
        name: str,
        channel: str,
        scene: Optional[str] = None,
        npc: Optional[str] = None,
        level: Optional[int] = None,
    ) -> Tag:
        """Create a new tag and return it."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO tags (name, channel, scene, npc, level)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, channel, scene, npc, level)
            )
            conn.commit()
            return Tag(
                id=cursor.lastrowid,
                name=name,
                channel=channel,
                scene=scene,
                npc=npc,
                level=level,
            )

    def get_tag(self, tag_id: int) -> Optional[Tag]:
        """Retrieve a tag by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, name, channel, scene, npc, level FROM tags WHERE id = ?",
                (tag_id,)
            )
            row = cursor.fetchone()
            if row:
                return Tag(id=row[0], name=row[1], channel=row[2], scene=row[3], npc=row[4], level=row[5])
            return None

    def get_tags_by_channel(self, channel: str) -> list[Tag]:
        """Retrieve all tags for a given channel."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, name, channel, scene, npc, level FROM tags WHERE channel = ?",
                (channel,)
            )
            return [
                Tag(id=row[0], name=row[1], channel=row[2], scene=row[3], npc=row[4], level=row[5])
                for row in cursor.fetchall()
            ]

    def update_tag(
        self,
        tag_id: int,
        name: Optional[str] = None,
        channel: Optional[str] = None,
        scene: Optional[str] = None,
        npc: Optional[str] = None,
        level: Optional[int] = None,
    ) -> Optional[Tag]:
        """Update a tag. Only provided fields are updated."""
        existing = self.get_tag(tag_id)
        if not existing:
            return None

        updated = Tag(
            id=tag_id,
            name=name if name is not None else existing.name,
            channel=channel if channel is not None else existing.channel,
            scene=scene if scene is not None else existing.scene,
            npc=npc if npc is not None else existing.npc,
            level=level if level is not None else existing.level,
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE tags
                SET name = ?, channel = ?, scene = ?, npc = ?, level = ?
                WHERE id = ?
                """,
                (updated.name, updated.channel, updated.scene, updated.npc, updated.level, tag_id)
            )
            conn.commit()

        return updated

    def delete_tag(self, tag_id: int) -> bool:
        """Delete a tag by ID. Returns True if deleted, False if not found."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_tags_by_scene(self, channel: str, scene: Optional[str] = None) -> int:
        """Delete all tags for a channel and scene. Returns count of deleted tags.

        If scene is None, deletes tags with no scene (default scene).
        """
        with sqlite3.connect(self.db_path) as conn:
            if scene is None:
                cursor = conn.execute(
                    "DELETE FROM tags WHERE channel = ? AND scene IS NULL",
                    (channel,)
                )
            else:
                cursor = conn.execute(
                    "DELETE FROM tags WHERE channel = ? AND scene = ?",
                    (channel, scene)
                )
            conn.commit()
            return cursor.rowcount

    def get_all_tags(self) -> list[Tag]:
        """Retrieve all tags."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, name, channel, scene, npc, level FROM tags"
            )
            return [
                Tag(id=row[0], name=row[1], channel=row[2], scene=row[3], npc=row[4], level=row[5])
                for row in cursor.fetchall()
            ]
