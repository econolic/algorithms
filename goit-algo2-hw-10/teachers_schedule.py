"""Create a class schedule with a greedy set-cover algorithm."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, EmailStr, Field, PositiveInt, field_validator

TEACHERS_FILE = Path(__file__).parent / "teachers.csv"


class TeacherProtocol(Protocol):
    """Protocol for teachers that can be used by the scheduler."""

    first_name: str
    last_name: str
    age: int
    email: str
    can_teach_subjects: set[str]
    assigned_subjects: set[str]


class Teacher(BaseModel):
    """University teacher with subjects they can teach and assigned subjects."""

    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    age: PositiveInt
    email: EmailStr
    can_teach_subjects: set[str] = Field(min_length=1)
    assigned_subjects: set[str] = Field(default_factory=set)

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Strip names and reject empty values."""
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("name must not be empty")

        return stripped_value


Teacher.model_rebuild()


def parse_subjects(subjects_text: str) -> set[str]:
    """Parse semicolon-separated subjects from a CSV cell."""
    subjects = {
        subject.strip() for subject in subjects_text.split(";") if subject.strip()
    }
    if not subjects:
        raise ValueError("teacher must have at least one subject")

    return subjects


def load_teachers_from_csv(csv_path: Path) -> list[Teacher]:
    """Load teachers from a CSV file."""
    teachers: list[Teacher] = []

    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            teachers.append(
                Teacher(
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    age=int(row["age"]),
                    email=row["email"],
                    can_teach_subjects=parse_subjects(row["can_teach_subjects"]),
                )
            )

    return teachers


def create_schedule(
    subjects: set[str], teachers: Sequence[TeacherProtocol]
) -> list[TeacherProtocol] | None:
    """Assign teachers to cover all subjects with a greedy set-cover algorithm.

    At each step the function chooses the teacher who covers the largest number
    of still-uncovered subjects. If several teachers cover the same number of
    subjects, the youngest teacher is selected.
    """
    uncovered_subjects = set(subjects)

    for teacher in teachers:
        teacher.assigned_subjects.clear()

    if not uncovered_subjects:
        return []

    teachable_subjects = set().union(
        *(teacher.can_teach_subjects for teacher in teachers)
    )
    if not uncovered_subjects.issubset(teachable_subjects):
        return None

    schedule: list[TeacherProtocol] = []
    available_teachers = list(teachers)

    while uncovered_subjects:
        best_teacher = max(
            available_teachers,
            key=lambda teacher: (
                len(teacher.can_teach_subjects & uncovered_subjects),
                -teacher.age,
            ),
        )
        assigned_subjects = best_teacher.can_teach_subjects & uncovered_subjects

        if not assigned_subjects:
            return None

        best_teacher.assigned_subjects.update(assigned_subjects)
        schedule.append(best_teacher)
        uncovered_subjects -= assigned_subjects
        available_teachers.remove(best_teacher)

    return schedule


if __name__ == "__main__":
    subjects_to_cover = {"Математика", "Фізика", "Хімія", "Інформатика", "Біологія"}
    teachers_list = load_teachers_from_csv(TEACHERS_FILE)

    schedule_result = create_schedule(subjects_to_cover, teachers_list)

    if schedule_result:
        print("Розклад занять:")
        for teacher_item in schedule_result:
            print(
                f"{teacher_item.first_name} {teacher_item.last_name}, "
                f"{teacher_item.age} років, email: {teacher_item.email}"
            )
            print(
                "   Викладає предмети: "
                f"{', '.join(sorted(teacher_item.assigned_subjects))}\n"
            )
    else:
        print("Неможливо покрити всі предмети наявними викладачами.")
