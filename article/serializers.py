from article.models import Article
from utils.api import serializers


class GetArticleSerializer(serializers.Serializer):
    """
    获取单个文章的检查类
    """
    article_id = serializers.IntegerField(min_value=0, required=True)


class CreateArticleSerializer(serializers.ModelSerializer):
    """
    创建文章的检查类
    """
    type = serializers.IntegerField()

    class Meta:
        model = Article
        fields = ('title', 'content', 'type',)
