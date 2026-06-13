# -*- coding: utf-8 -*-
import re
import requests
import time
from datetime import datetime
import ddddocr
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs


session = requests.session()


dl_url = "https://authserver.nuist.edu.cn/authserver/login?service=https%3A%2F%2Fi.nuist.edu.cn%2Flogin%23%2F"


dl = session.get(url=dl_url, allow_redirects=False)
print(session.cookies)
print(dl.status_code)



# 使用BeautifulSoup解析HTML
soup = BeautifulSoup(dl.text, 'html.parser')

# 查找id为"_eventId"的input标签
execution_tag = soup.find('input', id="execution")
pwdEncryptSalt_tag = soup.find('input', id="pwdEncryptSalt")
# 获取value属性
if execution_tag:
    execution = execution_tag['value']
    print(execution)
    # print("\n")
    pwdEncryptSalt = pwdEncryptSalt_tag['value']
    print(pwdEncryptSalt)
else:
    print("Input tag not found.")






now = datetime.now()
timestamp = int(now.timestamp() * 1000)
url = f'https://authserver.nuist.edu.cn/authserver/getCaptcha.htl?{timestamp}'
rzm_resp = session.get(url=url)
# print(rzm_resp.text)

# 如果请求成功，将图片保存到本地
if rzm_resp.status_code == 200:
    with open('Code.png', 'wb') as f:
        f.write(rzm_resp.content)
    print("Captcha image saved as captcha.jpg")
else:
    print("Failed to retrieve captcha image")



def OCR():
    ocr = ddddocr.DdddOcr()

    print("\n\n\n\n\n\n\n\n\n")

    f = open('Code.png', 'rb')
    with open('Code.png', 'rb') as f:  # 读取图片信息
        img_bytes = f.read()  # 识别验证码

    yzm = ocr.classification(img_bytes)
    print("\n初步识别验证码为：", yzm)

    return yzm


result = OCR()
print(result,"\n")



























import execjs

# 加载 JavaScript 文件，指定编码为 utf-8
with open('encryptPassword.js', 'r', encoding='utf-8') as file:
    js_code = file.read()

# 编译 JavaScript 代码
context = execjs.compile(js_code)

# 密码和盐值
password = "jzy000925."

# 调用 JavaScript 函数
encrypted_password = context.call('encryptPassword', password, pwdEncryptSalt)
print(encrypted_password)






url = "https://authserver.nuist.edu.cn/authserver/login?service=https%3A%2F%2Fi.nuist.edu.cn%2Flogin%23%2F"


# 创建一个字典，表示键值对
params = {
    'username': '2024XXXXXXXXXXXXXX',
    'password': encrypted_password,
    'captcha': result,
    '_eventId': 'submit',
    'cllt': 'userNameLogin',
    'dllt': 'generalLogin',
    'lt':'',
    'execution': execution,
}

# 使用 urlencode 函数对字典进行 URL 编码
encoded_params = urlencode(params)

response = session.post(url=url,data=params,headers={"Content-Type":"application/x-www-form-urlencoded"}, allow_redirects=False)
print(response.status_code)

print(response.text)
print(response.headers)

print(response.headers.get('Location'))
Location = response.headers.get('Location')
cookie = response.headers.get('Set-Cookie')
print(cookie)


set_cookie = urlparse(cookie)

# 获取查询参数
query_params = parse_qs(set_cookie.query)
#
#     # 提取各个参数
# ticket = query_params.get('iPlanetDirectoryPro', [None])[0]
#
# headers = {"cookie": cookie}
