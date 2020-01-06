import base64
import datetime
import os
import random
import re
from base64 import b64encode
from io import BytesIO

from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from django.conf import settings
from django.utils.crypto import get_random_string
from envelopes import Envelope


def m_decrypt(encryption_list):
    """接收一组加密文，返回对应解密后的结果"""
    pri_key = RSA.importKey(settings.RSA_PRIVATE_KEY)
    cipher = PKCS1_v1_5.new(pri_key)
    results = []
    for encryption in encryption_list:
        res = b""
        if encryption:
            try:
                res = cipher.decrypt(base64.b64decode(encryption), None)
            except ValueError:
                return None
        results.append(res.decode())

    if len(results) != len(encryption_list):
        return None
    return results


def rand_str(length=32, type="lower_hex"):
    """
    生成指定长度的随机字符串或者数字, 可以用于密钥等安全场景
    :param length: 字符串或者数字的长度
    :param type: str 代表随机字符串，num 代表随机数字
    :return: 字符串
    """
    if type == "str":
        return get_random_string(
            length,
            allowed_chars="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
    elif type == "lower_str":
        return get_random_string(
            length, allowed_chars="abcdefghijklmnopqrstuvwxyz0123456789")
    elif type == "lower_hex":
        return random.choice(
            "123456789abcdef") + get_random_string(length - 1, allowed_chars="0123456789abcdef")
    else:
        return random.choice(
            "123456789") + get_random_string(length - 1, allowed_chars="123456789")


def build_query_string(kv_data, ignore_none=True):
    # {"a": 1, "b": "test"} -> "?a=1&b=test"
    query_string = ""
    for k, v in kv_data.items():
        if ignore_none is True and kv_data[k] is None:
            continue
        if query_string != "":
            query_string += "&"
        else:
            query_string = "?"
        query_string += (k + "=" + str(v))
    return query_string


def img2base64(img):
    with BytesIO() as buf:
        img.save(buf, "gif")
        buf_str = buf.getvalue()
    img_prefix = "data:image/png;base64,"
    b64_str = img_prefix + b64encode(buf_str).decode("utf-8")
    return b64_str


def datetime2str(value, format="iso-8601"):
    if format.lower() == "iso-8601":
        value = value.isoformat()
        if value.endswith("+00:00"):
            value = value[:-6] + "Z"
        return value
    return value.strftime(format)


def timestamp2utcstr(value):
    return datetime.datetime.utcfromtimestamp(value).isoformat()


def natural_sort_key(s, _nsre=re.compile(r"(\d+)")):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(_nsre, s)]


def send_email(smtp_config, from_name, to_email, to_name, subject, content):
    envelope = Envelope(from_addr=(smtp_config["email"], from_name),
                        to_addr=(to_email, to_name),
                        subject=subject,
                        html_body=content)
    return envelope.send(smtp_config["server"],
                         login=smtp_config["email"],
                         password=smtp_config["password"],
                         port=smtp_config["port"],
                         tls=smtp_config["tls"])


def get_env(name, default=""):
    return os.environ.get(name, default)


def default_username():
    # 生成默认用户名
    header = "No_Mooc_"
    name = header + rand_str(15)
    return name


def default_user_id():
    return rand_str(12, "lower_str")
