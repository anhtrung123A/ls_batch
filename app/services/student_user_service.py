from app.models.user_model import UserCreateInput
from app.repositories.leads_repository import LeadsRepository
from app.repositories.students_repository import StudentsRepository
from app.repositories.users_repository import UsersRepository
from app.services.password_hasher import PasswordHasher
from app.utils.password import generate_random_password


class StudentUserService:
    def __init__(
        self,
        students_repository: StudentsRepository,
        leads_repository: LeadsRepository,
        users_repository: UsersRepository,
        password_hasher: PasswordHasher,
    ):
        self.students_repository = students_repository
        self.leads_repository = leads_repository
        self.users_repository = users_repository
        self.password_hasher = password_hasher

    def create_user_for_student(self, student_id: int) -> tuple[int, str, str, str]:
        lead = self.leads_repository.find_by_converted_student_id(student_id)
        if not lead:
            raise ValueError("Converted lead not found.")

        email_raw = (lead.email or "").strip().lower()
        if not email_raw:
            raise ValueError("Lead email is required.")

        if self.users_repository.is_email_exists(email_raw):
            raise ValueError("Email already exists.")

        temp_password = generate_random_password()
        password_hash = self.password_hasher.hash_password(temp_password)
        full_name = lead.full_name or "Student"
        phone = lead.phone

        user_id = self.users_repository.create(
            UserCreateInput(
                full_name=full_name,
                email=email_raw,
                phone=phone,
                password_hash=password_hash,
            )
        )
        self.students_repository.link_to_user(student_id, user_id)
        return user_id, email_raw, full_name, temp_password
