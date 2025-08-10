## ###################################################################################################################
##  Program :   Day_Trade_Test
##  Author  :
##  Install :   pip3 install requests  inspect platform argparse 
##  Example :	Scaffolding for tests 
##  Notes   :
## ###################################################################################################################import pytest
from day_trade import business_logic_test



# Test cases for business_logic function 
# CURRENTLY A WASTE SINCE THE FUNCTION RETURNS VOID 
def test_business_logic():
   assert business_logic_test( 2, 3 ,5)  == 10:

