########################################################################
###################  RaspberryPiPicoW + MicroPython  ###################
##################  MicroPython v1.23.0 on 2024-06-02  #################
#======================================================================#
# WiFi Access Point + HTTP server                                      #
# Features:                                                            #
#   1. Display of temperature sensor value                             #
#   2. LED control                                                     #
########################################################################

import socket
import network, uos, machine
import time
from usys import exit

led = machine.Pin("LED", machine.Pin.OUT)
led.on()

led1 = machine.PWM(machine.Pin(15))
led1.freq(100)

time.sleep(1)
led.off()

ap = network.WLAN(network.AP_IF)
#ap.config(essid='PicoW', password='123456789')
ap.config(essid='PicoW', security=0)
#ap.config(essid='PicoW', channel=9, security=0)
ap.active(True)

while ap.active() == False:
    pass

print('Access Point successful')
print(ap.ifconfig())
#=======================================================================
def web_page_temp(temp):
    html = """HTTP/1.1 200 OK\r
Server: PicoW\r
Content-Type: text/html\r
Connection: close\r
\r
<!DOCTYPE HTML>
<html>
<head>
<meta http-equiv="refresh" content="5">\r
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<center><h1>Hello, World!</h1></center>
<center><p>temprature: {:.1f} C</p></center>
<hr><center>Raspberry Pi Pico W</center>
</body>
</html>
"""
    return html.format(temp)
#=======================================================================
def web_page_error(err):
    html = """HTTP/1.1 200 OK\r
Server: PicoW\r
Content-Type: text/html\r
Connection: close\r
\r
<!DOCTYPE HTML>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<center><h1>{}</h1></center>
<hr><center>Raspberry Pi Pico W</center>
</body>
</html>
"""
    return html.format(err)
#=======================================================================
def web_page(msg):
    html = """HTTP/1.1 200 OK\r
Server: PicoW\r
Content-Type: text/html\r
Connection: close\r
\r
<!DOCTYPE HTML>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<center><h4>{}</h4></center>
<center><a href=\"sensor_temp.html\" target=\"_blank\">Temperature</a></center>
<center><a href=\"control.html\" target=\"_blank\">Control</a></center>
<hr><center>Raspberry Pi Pico W</center>
</body>
</html>
"""
    return html.format(msg)
#=======================================================================
def resp_headers(val):
    html = """HTTP/1.1 200 OK\r
Server: PicoW\r
Content-Type: {}\r
Connection: close\r
\r
"""
    return html.format(val)
#=======================================================================
def read_headers(sock, timeout):
    sock.settimeout(timeout)
    h = []
    t = None
    n = 0
    while n < 16:
        try:
            t = sock.readline()
            if len(t) < 3:
                break
        except  Exception as err:
            print("Error read from socket: {}".format(err))
            return ''
        h.append(t.decode())
        n += 1
    return h
#=======================================================================
def send_file(cl_sock, name, cont_type):
    response = resp_headers(cont_type)
    f = open(name, 'rb')
    file_ = f.read()
    f.close()
    cl_sock.sendall(response)
    cl_sock.sendall(file_)
#=======================================================================
def set_led1(cl_sock, uri_):
    data = float(uri_[10:])
    if (data < 0) or (data > 100):
        msg = 'Error data: {}'.format(data)
    else:
        msg = "led1: {} %".format(data)
        led1.duty_u16(int(65536/100 * data))
    print("msg: {}\n".format(msg))
    resp = """HTTP/1.1 200 OK\r
Server: PicoW\r
Content-Type: text/plain\r
Content-Length: {}\r
Connection: close\r
\r
{}"""
    resp = resp.format(len(msg), msg)
    cl_sock.sendall(resp)
#=======================================================================
def get_index(list_, msg):
    html = """HTTP/1.1 200 OK\r
Server: PicoW\r
Content-Type: text/html\r
Connection: close\r
\r
<!DOCTYPE HTML>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
{}<hr><center>Raspberry Pi Pico W</center>
</body>
</html>"""
    lst = '<center><h4>{}</h4></center>\n'.format(msg)
    lst += '<center><a href=\"sensor_temp.html\" target=\"_blank\">Temperature</a></center>\n'
    for h in list_:
        lst += '<center><a href=\"{}\" target=\"_blank\">{}</a></center>\n'.format(h, h)

    return html.format(lst)
#=======================================================================
def error_500(cl_sock):
    html = """HTTP/1.1 200 OK\r
Server: PicoW\r
Content-Type: text/html\r
Connection: close\r
\r
<!DOCTYPE HTML>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<center><h1>500 Internal Server Error</h1></center>
<hr><center>Raspberry Pi Pico W</center>
</body>
</html>
"""
    try:
        cl_sock.sendall(html)
    except  Exception as err:
        print("Error send to client: {}\n".format(err))
#=======================================================================
def client(cl_sock):
    global led_control
    uri = ''
    user_agent = ''
    hdrs = read_headers(cl_sock, 10)
    if len(hdrs) > 0:
        print('{}'.format(hdrs[0].strip()))
        for hd in hdrs:
            if hd[0:4] == 'User':
                user_agent = hd.strip()
                print("{}".format(user_agent))
        
        uri = hdrs[0].split()[1].strip()
        print("uri: {}".format(uri))
        if uri == '/sensor_temp.html':
            sensor_temp = machine.ADC(4)
            conversion_factor = 3.3 / (65535)
            reading = sensor_temp.read_u16() * conversion_factor 
            temp = (27 - (reading - 0.706)/0.001721)

            response = web_page_temp(temp)
            cl_sock.sendall(response)
        elif uri == '/':
            response = web_page(user_agent)
            cl_sock.sendall(response)
            #list_dir = uos.listdir('.')
            #response = get_index(list_dir, user_agent)
            #conn.sendall(response)
        elif uri == '/favicon.ico':
            path_ = uri[1:]
            print("path: {}\n".format(path_))
            send_file(cl_sock, path_, 'image/vnd.microsoft.icon')
        elif uri == '/1.txt':
            path_ = uri[1:]
            print("path: {}\n".format(path_))
            send_file(cl_sock, path_, 'text/plain')
        elif uri == '/control.html':
            resp = resp_headers('text/html')
            resp += led_control
            cl_sock.sendall(resp)
        elif '/led1?set=' == uri[0:10]:
            set_led1(cl_sock, uri)
        else:
            response = web_page_error('404 Not Found')
            cl_sock.sendall(response)
            print("404 Not Found\n")
#=======================================================================
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', 80))
s.listen(5)

def main_():
    print('***** Start Server *****')
    while True:
        print("\n***** wait connect *****")
        conn, addr = s.accept()
        led.on()
        conn.settimeout(10.0)

        print('Connection from {}'.format(addr))
        try:
            client(conn)
        except  Exception as err:
            print("Error client: {}".format(err))
            error_500(conn)
        conn.close()
        led.off()
########################################################################
led_control = """<!DOCTYPE HTML>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>test</title>
</head>
<body>
<form action="/led1" method="get">
<center><p id='led1'>led1: 0 %</p></center>
<center><p><input type="range" onchange="set_led1('set=', r1.value);" onwheel="set_val1('set=', r1.value);" id='r1' value="0" name="set1" min="0" max="100" step="0.1"></p></center>
</form>
<hr><center>Raspberry Pi Pico W</center>
<script>
 function set_led1(cmd, val) {
  var params  = cmd + val
  var http = new XMLHttpRequest();
  http.onreadystatechange = function()
  {
    if(this.readyState == 4)
    {
      if(this.status == 200)
      {
        if(this.responseText != null)
        {
          document.getElementById('led1').innerHTML = this.responseText
        }
        else alert("Ajax error: No data received")
      }
      else alert( "error: "+ this.status)
    }
  };
       
  http.open( "GET", "/led1?" + params, false );
  http.send();
  if (this.status == 200) document.getElementById('led1').innerHTML = http.responseText
    return xmlHttp.responseText;
 }
</script>
</body>
</html>
"""
########################################################################
main_()
