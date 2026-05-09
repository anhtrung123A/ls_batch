"""
How to run this job:
- Local/manual: `python scripts/run_job.py create_student_users --trigger manual`
- In Docker container and also write logs to `docker logs`:
  `docker exec batch sh -lc "cd /app && /usr/local/bin/python3 scripts/run_job.py create_student_users --trigger manual >> /proc/1/fd/1 2>> /proc/1/fd/2"`
"""

from app.constants.jobs import JOB_CREATE_STUDENT_USERS
from app.jobs.base_batch_job import BaseBatchJob
from app.models.batch_models import JobStats
from app.repositories.leads_repository import LeadsRepository
from app.repositories.students_repository import StudentsRepository
from app.repositories.users_repository import UsersRepository
from app.services.email_service import EmailService
from app.services.password_hasher import PasswordHasher
from app.services.student_user_service import StudentUserService


class CreateStudentUsersJob(BaseBatchJob):
    JOB_NAME = JOB_CREATE_STUDENT_USERS

    def __init__(self, connection, lock_owner: str = "batch-container"):
        super().__init__(connection=connection, job_name=self.JOB_NAME, lock_owner=lock_owner)
        self.students_repository = StudentsRepository(connection)
        self.student_user_service = StudentUserService(
            students_repository=self.students_repository,
            leads_repository=LeadsRepository(connection),
            users_repository=UsersRepository(connection),
            password_hasher=PasswordHasher(),
        )
        self.email_service: EmailService | None = None

    def set_email_service(self, email_service: EmailService):
        self.email_service = email_service

    def process(self, execution_id: int) -> JobStats:
        if self.email_service is None:
            raise RuntimeError("EmailService is required.")

        stats = JobStats()
        students = self.students_repository.find_without_user()
        self.logger.info("Found %s students with null user_id", len(students))

        for student in students:
            student_id = student.id
            student_code = student.student_code

            try:
                user_id, email_raw, full_name, temp_password = self.student_user_service.create_user_for_student(
                    student_id
                )
                self.email_service.send_student_created(
                    to_email=email_raw,
                    full_name=full_name,
                    password=temp_password,
                    student_code=student_code,
                )

                self.mark_item_success(execution_id, "student", student_id)
                self.connection.commit()
                stats.created += 1
                self.logger.info("Student %s linked to user %s", student_id, user_id)
            except ValueError as ex:
                self.connection.rollback()
                self.mark_item_skipped(execution_id, "student", student_id, str(ex))
                self.connection.commit()
                stats.skipped += 1
                self.logger.warning("Skipped student_id=%s: %s", student_id, ex)
            except Exception as ex:
                self.connection.rollback()
                self.mark_item_failed(execution_id, "student", student_id, str(ex))
                self.connection.commit()
                stats.failed += 1
                self.logger.exception("Failed processing student_id=%s", student_id)

        return stats
