import unittest
import requests

class TestAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.token = ""
        cls.poll_id = 0

        data = {
            "username" : "random_username"
        }
        response = requests.post("http://localhost:8080/polls/users/create", json=data)
        assert response.status_code == 200
        cls.token = response.json()['data']['token']

        data = {
            "title": "A title",
            "description" : "A random description",
            "user_id" : cls.token
        }
        response = requests.post("http://localhost:8080/polls/", json=data)
        assert response.status_code == 200
        assert type(response.json()['data']) == int
        cls.poll_id = response.json()['data']

    def test_failure_poll_creation(self):
        data = {
            "description" : "A poll description",
            "user_id" : self.token
        }
        response = requests.post("http://localhost:8080/polls/", json=data)
        assert response.status_code == 400
        assert response.json()['error'] == "The request is not well formed."

    def test_poll_details(self):
        response = requests.get("http://localhost:8080/polls/" + str(self.poll_id), None)
        assert response.status_code == 200
        assert response.json()['data']['polls']['description'] == "A random description"
        assert type(response.json()['data']['votes']) == list
        assert len(response.json()['data']['votes']) == 8

    def test_not_existing_poll(self):
        response = requests.get("http://localhost:8080/polls/123444", None)
        assert response.status_code == 200
        assert type(response.json()['data']['polls']) ==  type(None)

    def test_edit_poll(self):
        data = {
            "title"  : "A brand new title"
        }
        response = requests.post("http://localhost:8080/polls/" + str(self.poll_id), json=data)
        assert response.status_code == 200
        assert response.json()['data'] == "Poll correctly modified."

    def test_failure_edit_poll(self):
        data = {
            "title"  : ""
        }
        response = requests.post("http://localhost:8080/polls/" + str(self.poll_id), json=data)
        assert response.status_code == 400
        assert response.json()['error'] == "Some field in the request are empty."


    def test_list_user_poll(self):
        response = requests.get("http://localhost:8080/polls/users/" + self.token)
        assert response.status_code == 200
        assert len(response.json()['data']['polls']) == 1
        assert response.json()['data']['polls'][0]['id'] == self.poll_id
        assert response.json()['data']['polls'][0]['username'] == "random_username"

    def test_list_not_existing_user(self):
        fake_user = self.token + "123444"
        response = requests.get("http://localhost:8080/polls/users/" + fake_user)
        assert response.status_code == 200
        assert response.json()['data']['polls'] == []

    def test_cast_vote(self):
        url = "http://localhost:8080/polls/{}/users/{}/vote".format(self.poll_id, self.token)
        data ={
            "value" : "5"
        }
        response = requests.post(url, json = data)
        assert response.status_code == 200
        assert response.json()['data'] == "The vote has been registerd."

    def test_failure_cast_vote(self):
        url = "http://localhost:8080/polls/{}/users/{}/vote".format(self.poll_id, self.token)
        data ={
            "value" : "5345"
        }
        response = requests.post(url, json = data)
        assert response.status_code == 400
        assert response.json()['error'] == "Invalid vote value."

    def test_failure_cast_vote_fake_user(self):
        fake_user = self.token + "123444"
        url = "http://localhost:8080/polls/{}/users/{}/vote".format(self.poll_id, fake_user)
        data ={
            "value" : "5"
        }
        response = requests.post(url, json = data)
        assert response.status_code == 400
        assert response.json()['error'] == "Inserting vote has encountered an error."



if __name__ == '__main__':
    unittest.main()
