#  fb0dfd5592ed4eb19cd886d737b6cc6a
import requests
# Python源码资料电子书领取群 279199867
 
def send_wechat(msg):
    token = 'fb0dfd5592ed4eb19cd886d737b6cc6a'#前边复制到那个token
    title = 'title1'
    content = msg
    template = 'html'
    url = f"https://www.pushplus.plus/send?token={token}&title={title}&content={content}&template={template}"
    print(url)
    r = requests.get(url=url)
    print(r.text)
 
if __name__ == '__main__':
    msg = 'Life is short I use python'
    send_wechat(msg)