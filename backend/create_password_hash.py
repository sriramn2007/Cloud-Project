from getpass import getpass
from auth import _hash_password

if __name__ == "__main__":
    print(_hash_password(getpass("Password: ")))
