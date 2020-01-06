from rest_framework import serializers


class UserNameSerializer(serializers.Serializer):
    real_name = serializers.SerializerMethodField()
    user_id = serializers.CharField()

    def get_real_name(self, obj):
        return obj.userprofile.real_name

    # def __init__(self, *args, **kwargs):
    #     self.need_real_name = kwargs.pop("need_real_name", False)
    #     super().__init__(*args, **kwargs)

#
# class GradeInfoSerializer(serializers.Serializer):
#
#     level = serializers.CharField(max_length=6)
#     major = serializers.CharField(max_length=20)
#     class_id = serializers.IntegerField()

# class _JSONSerializer(JSONSerializer):
#     """docstring for M_"""
#
#     def dumps(self, obj):
#         return json.dumps(
#             obj,
#             separators=(
#                 ',',
#                 ':'),
#             cls=DjangoJSONEncoder).encode('latin-1')
#
#     def loads(self, data):
#         return json.loads(data.decode('latin-1'))
