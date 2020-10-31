
# Create your tests here.
from article.db_manager.article_manager import create_article_db
from utils.api.tests import APIClient, APITestCase
from utils.constants import ArticleTypeChoice
from utils.shortcuts import rand_str


def mock_create_article(title=None, content=None, art_type=None, owner_id=None):
    title = title or rand_str(type='str')
    content = content or rand_str(type='str')
    art_type = art_type or ArticleTypeChoice[0][1]
    owner_id = owner_id or 1
    return create_article_db(title, content, art_type, owner_id)


class ArticleViewTest(APITestCase):

    def setUp(self):
        self.client = APIClient()

    def test_create_article_view(self):
        self.create_user('maxin', 'password', login=True)
        article = mock_create_article()
        result = self.client.get('/api/article/', data={'article_id': 1}).json()
        self.assertEqual(result['result'], 'successful')
        self.assertEqual(result['data']['title'], article.title)
