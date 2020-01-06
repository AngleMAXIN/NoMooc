# !/usr/bin/env python
# -*- coding:utf-8 -*-

import xlrd


def open_file(file_path):
    file = xlrd.open_workbook(filename=file_path)

    table = file.sheets()[0]
    column_num, rows_num = table.ncols ,table.nrows
    if rows_num < 4 or column_num < 2:
        return "文件不合格"
    print("row :%s, cole: %s" % (rows_num, column_num))

    _START_LINE = 2
    userd = []
    for line in range(_START_LINE,rows_num):
        row_value = table.row_values(line)
        userd.append(row_value)

    for i in userd:
        print(id(i))

    for i in range(len(userd)):
        print(id(userd[i]))

if __name__ == '__main__':
    file_path  = "./导入学生.xlsx"
    open_file(file_path)
