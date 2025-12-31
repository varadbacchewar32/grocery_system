from typing import Any


from werkzeug.security import generate_password_hash , check_password_hash
class Users():
    n = "varad"
    p = "varad"

    def __init__(self , n , p , a):
        self.name = n
        self.password = generate_password_hash(p) 
        self.add = a
    def check_password(self, p):
        return check_password_hash(self.password, p)
v = Users("varad" , "password", "vadd")
print(v.check_password("Password"))
