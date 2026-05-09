from app.jobs.create_student_users_job import CreateStudentUsersJob
from app.services.email_service import EmailService


def build_jobs(connection, settings):
    def create_student_users():
        job = CreateStudentUsersJob(connection)
        job.set_email_service(EmailService(settings))
        return job

    return {
        CreateStudentUsersJob.JOB_NAME: create_student_users,
    }
