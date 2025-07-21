def binary(n):
    result=""
    while(n>0):
        a=n%2
        result=str(a)+result
        n=n//2
    print(result)
    
def octal(n):
    result=""
    while(n>0):
        a=n%8
        result=str(a)+result
        n=n//8
    print(result)
    
def hexadecimal(n):
    result=""
    while(n>0):
        a=n%16
        result=str(a)+result
        n=n//16
    print(result)
    
               
binary(10)
hexadecimal(69)
octal(100)