class AuthService:
    # Danh sách người dùng cơ bản (Tên đăng nhập: (Mật khẩu, Vai trò))
    USERS = {
        "admin": ("admin", "admin"),
        "engineer": ("engineer", "engineer"),
    }

    def __init__(self):
        self.current_user = None
        self.current_role = "worker"  # Mặc định là worker (chỉ xem/vận hành)

    def login(self, username: str, password: str) -> tuple[bool, str]:
        if not username:
            return False, "Username is required."
            
        user_info = self.USERS.get(username)
        if user_info and user_info[0] == password:
            self.current_user = username
            self.current_role = user_info[1]
            return True, f"Logged in successfully as {self.current_role.capitalize()}."
        
        return False, "Invalid username or password."

    def logout(self) -> str:
        self.current_user = None
        self.current_role = "worker"
        return "Logged out. Reverted to Worker role."

    def has_permission(self, required_role: str) -> bool:
        roles = ["worker", "engineer", "admin"]
        try:
            current_level = roles.index(self.current_role)
            required_level = roles.index(required_role)
            return current_level >= required_level
        except ValueError:
            return False
