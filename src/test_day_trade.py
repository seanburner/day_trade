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
   assert str(business_logic_test( current_time = "2025-08-16 16:01:10",  time_interval  = 900 ) ) == "2025-08-16 16:15:10"

