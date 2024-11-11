from states import UserState

class UserSession:
    def __init__(self):
        self.sessions = {}

    def get_session(self, sender):
        if sender not in self.sessions:
            self.sessions[sender] = {"state": UserState.WELCOME, "data": {}}
        return self.sessions[sender]

    def update_state(self, sender, new_state):
        self.get_session(sender)["state"] = new_state

    def update_data(self, sender, key, value):
        self.get_session(sender)["data"][key] = value

session_manager = UserSession()
