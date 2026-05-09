from app.constants.jobs import JOB_CREATE_LEADS_FROM_EXCEL
from app.jobs.create_leads_from_excel_job import CreateLeadsFromExcelJob
from app.jobs.create_student_users_job import CreateStudentUsersJob
from app.services.email_service import EmailService


def build_jobs(connection, settings):
    def create_student_users():
        job = CreateStudentUsersJob(connection)
        job.set_email_service(EmailService(settings))
        return job

    def create_leads_from_excel():
        return CreateLeadsFromExcelJob(connection, settings)

    return {
        CreateStudentUsersJob.JOB_NAME: create_student_users,
        JOB_CREATE_LEADS_FROM_EXCEL: create_leads_from_excel,
    }
