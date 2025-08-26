## ###################################################################################################################
##  Program :   Day_Trade_Test
##  Author  :
##  Install :   pip3 install requests  inspect platform argparse 
##  Example :	Scaffolding for tests 
##  Notes   :
## ###################################################################################################################import pytest
from day_trade import business_logic_test
from datetime  import datetime



# Test cases for business_logic function 
# CURRENTLY A WASTE SINCE THE FUNCTION RETURNS VOID 
def test_business_logic():
   poll_time = business_logic_test( current_time = "2025-08-16 16:01:10",  time_interval  = 900 )
   assert f"{poll_time}" == "2025-08-16 16:15:10"

