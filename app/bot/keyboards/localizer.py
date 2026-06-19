from app.database.models import TaskStatus, TaskPriority, TaskType

STATUS_EMOJI: dict = {
    TaskStatus.NEW: "🔵",
    TaskStatus.IN_PROGRESS: "🟡",
    TaskStatus.WAITING_APPLICANT: "🟠",
    TaskStatus.WAITING_EXECUTOR: "🟣",
    TaskStatus.DONE: "🟢",
    TaskStatus.CANCELLED: "🔴",
}

STATUS_TEXT: dict = {
    TaskStatus.NEW: "Новий",
    TaskStatus.IN_PROGRESS: "В процесі",
    TaskStatus.WAITING_APPLICANT: "Очікує на підтвердження Заявником",
    TaskStatus.WAITING_EXECUTOR: "Очікує на підтвердження Виконавцем",
    TaskStatus.DONE: "Виконано",
    TaskStatus.CANCELLED: "Скасовано",
}

PRIORITY_TEXT: dict = {
    TaskPriority.LOW: "Низький",
    TaskPriority.MEDIUM: "Середній",
    TaskPriority.HIGH: "Високий",
}

TYPE_TEXT: dict = {
    TaskType.SYSTEM: "Системний",
    TaskType.LOCAL: "Локальний",
}