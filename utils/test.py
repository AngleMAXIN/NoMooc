# import os
# import zipfile
#
#
# def zip_test_cases(test_case_path):
#     start_dir = test_case_path  # 要压缩的文件夹路径
#     file_news = test_case_path + '.zip'  # 压缩后文件夹的名字
#
#     z = zipfile.ZipFile(file_news, 'w', zipfile.ZIP_DEFLATED)
#     for dir_path, dir_names, file_names in os.walk(start_dir):
#         f_path = dir_path.replace(start_dir, '')  # 这一句很重要，不replace的话，就从根目录开始复制
#         f_path = f_path and f_path + os.sep or ''  # 实现当前文件夹以及包含的所有文件的压缩
#         for filename in file_names:
#             z.write(os.path.join(dir_path, filename), f_path + filename)
#     z.close()
#     return file_news
#
#
# zip_test_cases("/data/backend/test_case")
print("我来签到啦%\(^_^)/%!")