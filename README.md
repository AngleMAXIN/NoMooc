# NoMooc本地环境安装

#### 命名规范

- **pr 标题**、**commit 信息** 必须以 `功能关键字:` 开头，命名形式为`[功能关键字]: [名称]`，**分支** 名必须以 `功能关键字/`开头，命名形式为`[功能关键字]/[名称]`

  功能关键字介绍如下：

  - feat :sparkles: - 新功能（feature）
  - refactor :hammer: - 重构原有功能或模块
  - fix :bug: - 修补 bug
  - docs :memo: - 文档（document）
  - style :lipstick: - 格式（不影响代码运行的变动）
  - test :white_check_mark: - 增加测试
  - chore :green_heart: - 构建过程或辅助工具的变动
  - revert - 撤销
  - close - 关闭 issue
  - release - 发布版本
  
### Curr_Env

```
python 3.6
mysql 5.7
redis 3.0.6
django 1.1.14
```

- **数据库配置根据本地做相应修改**

  ```json
  # oj/dev_setting.py
  
  DATABASES = {
      "default": {
          "ENGINE": "django.db.backends.mysql",
          "HOST": "127.0.0.1",
          "PORT": "3306",
          "NAME": "oj_database",
          "USER": "root",
          "PASSWORD": "xxxxxx",
          "CHARSET": "utf8",
  
      }
  }
  
  REDIS_CONF = {
      "host": "127.0.0.1",
      "port": "6379"
  }
  
  ```

- **安装依赖库**

  ```
  pip install --no-cache-dir -r deploy/requirements.txt -i https://pypi.douban.com/simple
  ```

- **初始化数据库**

  ```
  # python3 manage.py makemigrations
  # python3 manage.py migrate
  ```

- **修改deploy/supervisord_local.conf文件**

  ```
  [program:task_celery]
  command=/root/.pyenv/shims/celery -A oj worker -l warning
  ;directory=/OnlineJudge/
  stdout_logfile=data/log/task_celery.log
  stderr_logfile=data/log/task_celery.log
  autostart=true
  autorestart=true
  startsecs=5
  stopwaitsecs = 5
  killasgroup=true
  
  
  [program:beat_celery]
  command=/root/.pyenv/shims/celery -A oj beat -l warning
  stdout_logfile=data/log/celery_beat.log
  stderr_logfile=data/log/celery_beat.log
  autostart=true
  autorestart=true
  startsecs=5
  stopwaitsecs = 5
  killasgroup=true
  
  
  [program:gunicorn]
  command=/root/.pyenv/shims/gunicorn oj.wsgi -b 127.0.0.1:8080 --reload -w 3 -k gevent
  stdout_logfile=data/log/gunicorn.log
  stderr_logfile=data/log/gunicorn.log
  autostart=true
  autorestart=true
  startsecs=5
  stopwaitsecs = 5
  killasgroup=true
  
  ```

  > 将`/root/.pyenv/shims/celery`以及`/root/.pyenv/shims/gunicorn`的执行路径，换为你本地的执行路径，我这里是虚拟环境的执行路径

如果一切正常，服务将监听在 `127.0.0.1:8080`