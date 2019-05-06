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

    

if __name__ == '__main__':
    unittest.main()
