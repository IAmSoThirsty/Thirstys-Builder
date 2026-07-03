from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Subject:
    subject_id: str
    display_name: str
    roles: tuple[str, ...] = field(default_factory=tuple)
    active: bool = True


class IdentityRegistry:
    def __init__(self, subjects: list[Subject] | None = None) -> None:
        self._subjects: dict[str, Subject] = {}
        for subject in subjects or []:
            self.add(subject)

    def add(self, subject: Subject) -> None:
        if not subject.subject_id:
            raise ValueError("subject_id is required")
        self._subjects[subject.subject_id] = subject

    def resolve(self, subject_id: str) -> Subject | None:
        subject = self._subjects.get(subject_id)
        if subject is None or not subject.active:
            return None
        return subject
