import json

from account.decorators import login_required
from article.db_manager.article_manager import create_article_db, get_article_by_id_db, build_article_detail_info
from article.serializers import CreateArticleSerializer, GetArticleSerializer
from utils.api import APIView, validate_serializer


class ArticleAPI(APIView):
    """
    文章
    """

    @validate_serializer(GetArticleSerializer)
    @login_required
    def get(self, request):
        """
        获取文章
        """
        article_id = request.data['article_id']
        article = get_article_by_id_db(article_id)
        if not article:
            return self.error('文章不存在')

        article_info = build_article_detail_info(article)
        return self.success(data=article_info)

    @validate_serializer(CreateArticleSerializer)
    # @login_required
    def post(self, request):
        """
        创建文章
        """
        title = request.data['title']
        content = request.data['content']
        art_type = request.data['type']
        owner_id = request.session.get('_auth_user_id')

        create_article_db(title=title, content=content, art_type=art_type, owner_id=owner_id)
        return self.success()
