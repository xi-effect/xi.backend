from flask.testing import FlaskClient

from .components import check_status_code


def test_set_avatar_user(client: FlaskClient):
    with open('test/files/1.jpg', 'rb') as f:
        image1 = f.read()

    check_status_code(client.post('/avatar/', data=image1))
    assert check_status_code(client.get('/avatar/'), get_json=False).get_data() == image1

    with open('test/files/0.png', 'rb') as f:
        image2 = f.read()

    check_status_code(client.post('/avatar/', data=image2))
    assert check_status_code(client.get('/avatar/'), get_json=False).get_data() == image2

    check_status_code(client.delete('/avatar/'))
    check_status_code(client.get('/avatar/'), 404)
