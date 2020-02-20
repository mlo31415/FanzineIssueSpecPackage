# A FanzineIssueSpec contains the information for one fanzine issue's specification, e.g.:
#  V1#2, #3, #2a, Dec 1967, etc.
# It can be a volume+number or a whole numer or a date. (It can be more than one of these, also, and all are retained.)
from __future__ import annotations

import math
import re
from typing import Union, Tuple, Optional

import roman
from functools import reduce
import datetime
import dateutil.parser
import dateutil.parser

from HelpersPackage import ToNumeric, IsNumeric, IsInt
from HelpersPackage import RemoveHTMLDebris
from HelpersPackage import Log
from HelpersPackage import InterpretNumber
from HelpersPackage import CaseInsensitiveCompare


class FanzineDate:
    def __init__(self, Year=None, Month=None, MonthText=None, Day=None, DayText=None):
        self.Year=Year
        self.Month=Month
        self.MonthText=MonthText  # In case the month is specified using something other than a month name, we save the special text here
        self.Day=Day
        self.DayText=DayText  # In case the day is specified using something other than a numer (E.g., "Christmas Day"), we save the special text here

        #TODO: Where do these two go?
        #self.UninterpretableText=None  # Ok, I give up.  Just hold the text as text.
        #self.TrailingGarbage=None  # The uninterpretable stuff following the interpretable spec held in this instance

    def __eq__(self, other: FanzineDate) -> bool:
        # If we're checking against a null input, it's not equal
        if other is None:
            return False
        # If either date is entirely None, its not equal
        if self._Year is None and self._Month is None and self._Day is None:
            return False
        if other._Year is None and other._Month is None and other._Day is None:
            return False
        # OK, we know that both self and other have a non-None date element, so just check for equality
        return self._Year == other._Year and self._Month == other._Month and self._Day == other._Day

    def __ne__(self, other: FanzineDate) -> bool:
        return not self.__eq__(other)

    # -----------------------------
    # Define < operator for sorting
    def __lt__(self, other: FanzineDate) -> bool:
        if self._Year is None:
            return True
        if other._Year is None:
            return False
        if self._Year != other._Year:
            return self._Year < other._Year
        if self._Month is None:
            return True
        if other._Month is None:
            return False
        if self._Month != other._Month:
            return self._Month < other._Month
        if self._Day is None:
            return True
        if other._Day is None:
            return False
        if self._Day != other._Day:
            return self._Day < other._Day
        return False

    def Copy(self, other: FanzineDate):
        self._Year=other._Year
        self._Month=other._Month
        self._MonthText=other._MonthText
        self._Day=other._Day
        self._DayText=other._DayText
        #self._UninterpretableText=other._UninterpretableText
        #self._TrailingGarbage=other._TrailingGarbage

    # .....................
    @property
    def Year(self) -> int:
        return self._Year

    @Year.setter
    def Year(self, val: Union[int, str]):
        if isinstance(val, str):
            self._Year=ToNumeric(YearAs4Digits(val))
        else:
            self._Year=YearAs4Digits(val)

    # .....................
    # This is a non-settable property -- it is always derived from the numeric Year
    @property
    def YearText(self) -> str:
        return YearName(self._Year)

    # .....................
    @property
    def Month(self) -> int:
        return self._Month

    @Month.setter
    def Month(self, val: Union[int, str]):
        if isinstance(val, str):
            self._Month=InterpretMonth(val)
            self._MonthText=val
        else:
            self._Month=val
            self._MonthText=None  # If we set a numeric month, any text month gets blown away as no longer relevant

    # .....................
    @property
    def MonthText(self) -> str:
        if self._MonthText is not None:
            return self._MonthText
        if self._Month is not None:
            return MonthName(self._Month)
        return ""

    @MonthText.setter
    def MonthText(self, val: str):
        self._MonthText=val
        self._Month=InterpretMonth(val)
        # TODO: Compute the real month and save it in _Month

    # .....................
    @property
    def Day(self) -> int:
        return self._Day

    @Day.setter
    def Day(self, val: Union[int, str]):
        if isinstance(val, str):
            self._Day=ToNumeric(val)
            self._DayText=val
        else:
            self._Day=val
            self._DayText=None  # If we set a numeric month, any text month gets blown away as no longer relevant

    # .....................
    @property
    def DayText(self) -> Union[str, None]:
        if self._DayText is not None:
            return self._DayText
        if self._Day is not None:
            return DayName(self._Day)
        return None

    @DayText.setter
    def DayText(self, val: str):
        self._DayText=val
        # TODO: Compute the real day and save it in _Day

    # # .....................
    # @property
    # def UninterpretableText(self) -> str:
    #     return self._UninterpretableText
    #
    # @UninterpretableText.setter
    # def UninterpretableText(self, val: Optional[str]):
    #     if val is None:
    #         self._UninterpretableText=None
    #         return
    #     val=val.strip()
    #     if len(val) == 0:
    #         self._UninterpretableText=None
    #         return
    #     self._UninterpretableText=val
    #
    # # .....................
    # @property
    # def TrailingGarbage(self) -> str:
    #     return self._TrailingGarbage
    #
    # @TrailingGarbage.setter
    # def TrailingGarbage(self, val: Optional[str]):
    #     if val is None:
    #         self._TrailingGarbage=None
    #         return
    #     val=val.strip()
    #     if len(val) == 0:
    #         self._TrailingGarbage=None
    #         return
    #     self._TrailingGarbage=val

    # .....................
    @property
    def Date(self) -> Optional[str]:
        if not self.IsEmpty():
            return self.FormatYearMonthForSorting()
        return None
    # TODO Do this right

    # .....................
    # Return a datetime object
    def Datexxx(self) -> datetime:
        y=self._Year if self._Year is not None else 1
        m=self._Month if self._Month is not None else 1
        d=self._Day if self._Day is not None else 1
        return datetime.date(y, m, d)

    # .....................
    def SetDate(self, y: Union[int, str], m: Union[int, str]):
        self.Year=ToNumeric(y)
        self.Month=m

    # .......................
    # Convert the FanzineIssueSpec into a debugging form
    def DebugStr(self) -> str:
        #if self.UninterpretableText is not None:
        #    return"("+self.UninterpretableText+")"

        d=""
        if self.Year is not None:
            d=str(self.Year)
        if self.Month is not None:
            d=d+":"+str(self.Month)
        if self.MonthText is not None:
            d=d+":"+self.MonthText
        if self.Day is not None:
            d=d+"::"+str(self.Day)
        if self.DayText is not None:
            d=d+"::"+self.DayText
        if d == "":
            d="-"

        s="D"+d
        #if self.TrailingGarbage is not None:
        #    s=s+", TG='"+self.TrailingGarbage+"'"
        #if self.UninterpretableText is not None:
        #    s=s+", UT='"+self.UninterpretableText+"'"
        s=s+")"

        return s

    # .......................
    def IsEmpty(self) -> bool:
        return not reduce(lambda a, b: a or b, [self._DayText, self._Day, self._MonthText, self._Month, self._Year])

    # .......................
    # Convert the FanzineIssueSpec into a pretty string for display or printing
    def __str__(self) -> str:
        #if self.UninterpretableText is not None:
        #    return self.UninterpretableText.strip()

        tg=""
        #if self.TrailingGarbage is not None:
        #    tg=" "+self.TrailingGarbage

        # We don't treat a day without a month and year or a month without a year as valid and printable
        if self.Year is not None:
            if self.Month is None:
                tg=str(self.Year)+" "+tg
            elif self._MonthText is not None:
                tg=self._MonthText+" "+str(self._Year)+" "+tg  # There's never a monthtext+day combination
            elif self._DayText is not None:
                tg=self._DayText+" "+str(self._Year)+" "+tg
            else:
                tg=MonthName(self._Month, short=True)+" "+str(self._Day)+", "+str(self._Year)+" "+tg

        if len(tg) > 0:
            return tg.strip()
        return "(undated)"


    # =============================================================================
    def FormatYearMonthForSorting(self) -> str:
        if self._Year is None:
            return "0000-00-00"
        y=str(self._Year)
        m="00"
        if self._Month is not None:
            m=("00"+str(self._Month))[-2:]

        rslt=y+"-"+m
        if self._MonthText is not None:  # We add the month text on so that the sort separates dates with the same month number coming from different forms (e.g., Sept vis Sept-Oct)
            rslt+="-"+self._MonthText
        elif self._Month is not None:
            rslt+="-"+MonthName(self._Month)
        return rslt

    # --------------------------------
    # Parse a free-format string to find a date.  This tries to interpret the *whole* string as a date -- it doesn't find a date embeded in other text.
    def ParseGeneralDateString(self, s: str) -> FanzineDate:

        # Whitespace is not a date...
        dateText=s.strip()
        if len(dateText) == 0:
            return self

        # First just try dateutil on the string
        # If it works, we've got an answer. If not, we'll keep trying.
        try:
            d=dateutil.parser.parse(dateText, default=datetime.datetime(1, 1, 1))
            if d != datetime.datetime(1, 1, 1):
                self.Year=d.year
                self.Month=d.month
                self.Day=d.day
                self.Raw=dateText
                #self.Date=d
                #TODO: Do we want a datetime element at all?
                return self
        except:
            pass  # We'll continue with fancier things

        # There are some dates which follow no useful pattern.  Check for them
        d=InterpretRandomDatestring(dateText)
        if d is not None:
            self.Copy(d)
            return self

        # A common pattern of date that dateutil can't parse is <something> <some year>, where <something> might be "Easter" or "Q1" or "summer"
        # So look for strings of the format:
        #   Non-whitespace which includes at least one non-digit
        #   Followed by a number between 1920 and 2050 or followed by a number between 00 and 99 inclusive.
        # Take the first to be a strange-date-within-year string and the second to be a year string.

        # That used the dateutil parser which can handle a wide variety of date formats...but not all.
        # So the next step is to reduce some of the crud used by fanzines to an actual date.
        # Remove commas, which should never be significant
        dateText=dateText.replace(",", "").strip()

        ytext=None
        mtext=None

        m=re.compile("^(.+)\s+(\d\d|\d\d\d\d)$").match(dateText)  # Month + 2- or 4-digit year
        if m is not None and m.groups() is not None and len(m.groups()) == 2:
            mtext=m.groups()[0]
            ytext=m.groups()[1]
            if ytext is not None and mtext is not None:
                y=YearAs4Digits(ToNumeric(ytext))
                if y is not None and 1860 < y < 2100:  # Outside this range it can't be a fannish-relevant year (the range is oldest fan birth date to middle-future)
                    if InterpretMonth(mtext) is not None:
                        self.Year=ytext
                        md=InterpretMonthDay(mtext)
                        if md is not None:
                            self.Month=md[0]
                            self.Day=md[1]
                            self.Raw=dateText
                            return self

        # OK, neither of those worked work.
        # Assuming that a year was found, try one of the weird month-day formats.
        if ytext is not None and mtext is not None:
            rslt=InterpretNamedDay(mtext)  # mtext was extracted by whichever pattern recognized the year and set y to non-None
            if rslt is not None:
                self.Year=ytext
                self.MonthText=mtext
                self.Month=rslt[0]
                self.Day=rslt[1]
                self.Raw=dateText
                return self

        # That didn't work.
        # There are some words used to add days which are relative terms "late september", "Mid february" etc.
        # Give them a try.
        if ytext is not None and mtext is not None:
            # In this case the *last* token is assumed to be a month and all previous tokens to be the relative stuff
            tokens=mtext.replace("-", " ").replace(",", " ").split()
            if tokens is not None and len(tokens) > 0:
                modifier=" ".join(tokens[:-1])
                mtext=tokens[-1:][0]
                m=MonthNameToInt(mtext)
                d=InterpretRelativeWords(modifier)
                if m is not None and d is not None:
                    self.Year=ytext
                    self.Month=mtext
                    self.DayText=modifier
                    self.Day=d
                    self.Raw=dateText
                    return self

        # Nothing worked
        Log("   ***Date conversion failed: '"+s+"'", isError=True)
        return self


#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
class FanzineSerial:

    def __init__(self, Vol=None, Num=None, NumSuffix=None, Whole=None, WSuffix=None):
        self._Vol=Vol
        self._Num=Num
        self._NumSuffix=NumSuffix  # For things like issue '17a'
        self._Whole=Whole
        self._WSuffix=WSuffix
        #self._UninterpretableText=None  # Ok, I give up.  Just hold the text as text.
        #self._TrailingGarbage=None  # The uninterpretable stuff following the interpretable spec held in this instance

    # Are the Num fields equal?
    # Both could be None; otherwise both must be equal
    def __NumEq__(self, other) -> bool:
        return self._Num == other._Num and CaseInsensitiveCompare(self._NumSuffix, other._NumSuffix)

    def __VolEq__(self, other) -> bool:
        return self._Vol == other._Vol

    def __WEq__(self, other) -> bool:
        return self._Whole == other._Whole and CaseInsensitiveCompare(self._WSuffix, other._WSuffix)

    def __VNEq__(self, other) -> bool:
        return self.__VolEq__(other) and self.__NumEq__(other)

    # Two issue designations are deemed to be equal if they are identical or if the VN matches while at least on of the Wholes in None or
    # is the Whole matches and at least one of the Vs and Ns is None.  (We would allow match of (W13, V3, N2) with (W13), etc.)
    def __eq__(self, other):
        if self.__VNEq__(other) and self.__WEq__(other):
            return True
        if (self._Whole is None or other._Whole is None) and self.__VNEq__(other):
            return True
        if (self._Num is None or self._Vol is None or other._Num is None or other._Vol is None) and self.__WEq__(other):
            return True
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    # -----------------------------
    # Define < operator for sorting
    def __lt__(self, other: FanzineSerial):
        if other is None:
            return False
        # If both have Wholes, use that
        if self._Whole is not None and other._Whole is not None:
            if self._Whole < other._Whole:
                return True
            if self._Whole > other._Whole:
                return False
            # OK, the Wholes must be equal.  See if one of them has a suffix (e.g., #133 and #133A). Suffixed Wholes are always larger.
            if self._WSuffix is None and other._WSuffix is None:
                return False
            if self._WSuffix is None and other._WSuffix is not None:
                return True
            if self._WSuffix is not None and other._WSuffix is None:
                return False
            # Both have suffixes
            return self._WSuffix < other._WSuffix

        if self._Vol is not None and other._Vol is not None:
            if self._Vol < other._Vol:
                return True
            if self._Vol > other._Vol:
                return False
            # The Vols are equal; Check the numbers within the volume
            if self._Num is None and other._Num is None:
                return False
            if self._Num is None and other._Num is not None:
                return True
            if self._Num is not None and other._Num is None:
                return False

        # Who knows?
        return False


    def Copy(self, other: FanzineSerial):
        self._Vol=other._Vol
        self._Num=other._Num
        self._NumSuffix=other._NumSuffix
        self._Whole=other._Whole
        self._WSuffix=other._WSuffix
        self._UninterpretableText=other._UninterpretableText
        self._TrailingGarbage=other._TrailingGarbage

    # .....................
    @property
    def Vol(self) -> Optional[int]:
        return self._Vol

    @Vol.setter
    def Vol(self, val: Optional[int, str]):
        self._Vol=ToNumeric(val)

    # .....................
    @property
    def Num(self) -> Optional[int]:
        return self._Num

    @Num.setter
    def Num(self, val: Optional[int, str]):
        self._Num=ToNumeric(val)

    # .....................
    @property
    def NumSuffix(self) -> Optional[str]:
        return self._NumSuffix

    @NumSuffix.setter
    def NumSuffix(self, val: Optional[str]):
        self._NumSuffix=val

    # .....................
    @property
    def Whole(self) -> Optional[int]:
        return self._Whole

    @Whole.setter
    def Whole(self, val: Optional[int, str]):
        self._Whole=ToNumeric(val)

    # .....................
    @property
    def WSuffix(self) -> Optional[str]:
        return self._WSuffix

    @WSuffix.setter
    def WSuffix(self, val: Optional[str]):
        self._WSuffix=val

    # # .....................
    # @property
    # def UninterpretableText(self) -> Optional[str]:
    #     return self._UninterpretableText
    #
    # @UninterpretableText.setter
    # def UninterpretableText(self, val: Optional[str]):
    #     if val is None:
    #         self._UninterpretableText=None
    #         return
    #     val=val.strip()
    #     if len(val) == 0:
    #         self._UninterpretableText=None
    #         return
    #     self._UninterpretableText=val

    # .....................
    @property
    # def TrailingGarbage(self) -> Optional[str]:
    #     return self._TrailingGarbage
    #
    # @TrailingGarbage.setter
    # def TrailingGarbage(self, val: Optional[str]):
    #     if val is None:
    #         self._TrailingGarbage=None
    #         return
    #     val=val.strip()
    #     if len(val) == 0:
    #         self._TrailingGarbage=None
    #         return
    #     self._TrailingGarbage=val

    @property
    def Serial(self) -> Optional[str]:
        if not self.IsEmpty():
            return self.FormatSerialForSorting()
        return None

        # TODO Do this right

        # .....................
        # Does this class have anything defined for the serial number?
    def IsEmpty(self) -> bool:
        return not reduce(lambda a, b: a or b, [self._NumSuffix, self._Num, self._Whole, self._WSuffix, self._Vol])

        # .....................
    def SetWhole(self, num: int, suffix: str):
        self.Whole=num
        if suffix is None:
            return self
        if len(suffix) == 1 and suffix.isalpha():  # E.g., 7a
            self.WSuffix=suffix
        elif len(suffix) == 2 and suffix[0] == '.' and suffix[1].isnumeric():  # E.g., 7.1
            self.WSuffix=suffix
        # else:
        #     self.TrailingGarbage=suffix
        return self

        # .......................
        # Convert the FanzineIssueSpec into a debugging form
    def DebugStr(self) -> str:
        # if self.UninterpretableText is not None:
        #     return "IS("+self.UninterpretableText+")"

        v="-"
        if self.Vol is not None:
            v=str(self.Vol)
        n="-"
        if self.Num is not None:
            n=str(self.Num)
            if self.NumSuffix is not None:
                n+=str(self.NumSuffix)
        w="-"
        if self.Whole is not None:
            w=str(self.Whole)
            if self.WSuffix is not None:
                w+=str(self.WSuffix)

        s="V"+v+", N"+n+", W"+w
        # if self.TrailingGarbage is not None:
        #     s+=", TG='"+self.TrailingGarbage+"'"
        # if self.UninterpretableText is not None:
        #     s+=", UT='"+self.UninterpretableText+"'"
        return s

        # .......................
        # Convert the FanzineIssueSpec into a pretty string for display or printing

    def __str__(self):
        # if self.UninterpretableText is not None:
        #     return self.UninterpretableText.strip()

        tg=""
        # if self.TrailingGarbage is not None:
        #     tg=" "+self.TrailingGarbage

        if self.Vol is not None and self.Num is not None and self.Whole is not None:
            s="V"+str(self.Vol)+"#"+str(self.Num)
            if self.NumSuffix is not None:
                s+=str(self.NumSuffix)
            s+=" (#"+str(self.Whole)
            if self.WSuffix is not None:
                s+=str(self.WSuffix)
            s+=")"
            tg=(s+tg).strip()

        elif self.Vol is not None and self.Num is not None:
            s="V"+str(self.Vol)+"#"+str(self.Num)
            if self.NumSuffix is not None:
                s+=str(self.NumSuffix)
            tg=(s+tg).strip()

        elif self.Whole is not None:
            s="#"+str(self.Whole)
            if self.WSuffix is not None:
                s+=str(self.WSuffix)
            tg=(s+tg).strip()

        return tg.strip()

     # =====================================================================================
        # Function to attempt to decode an issue designation into a volume and number
        # Return a tuple of Volume and Number
        # If there's no volume specified, Volume is None and Number is the whole number
        # If we can't make sense of it, return (None, None), so if the 2nd member of the tuple is None, conversion failed.
    def DecodeIssueDesignation(self, s: str) -> Tuple[ Optional[int], Optional[int] ]:
        try:
            return None, int(s)
        except:
            pass  # A dummy statement since all we want to do with an exception is move on to the next option.

        # Ok, it's not a simple number.  Drop leading and trailing spaces and see if it of the form #nn
        s=s.strip().lower()
        if len(s) == 0:
            return None, None
        if s[0] == "#":
            s=s[1:]
            if len(s) == 0:
                return None, None
            try:
                return None, int(s)
            except:
                pass  # A dummy statement since all we want to do with an exception is move on to the next option.

        # This exhausts the single number possibilities
        # Maybe it's of the form Vnn, #nn (or Vnn.nn or Vnn,#nn)

        # Strip any leading 'v'
        if len(s) == 0:
            return None, None
        if s[0] == "v":
            s=s[1:]
            if len(s) == 0:
                return None, None

        # The first step is to see if there's at least one of the characters ' ', '.', and '#' in the middle
        # We split the string in two by a span of " .#"
        # Walk through the string until we;ve passed the first span of digits.  Then look for a span of " .#". The look for at least one more digit.
        # Since we've dropped any leading 'v', we kno we must be of the form nn< .#>nnn
        # So if the first character is not a digit, we give up.
        if not s[0].isdigit():
            return None, None

        # Now, the only legitimate character other than digits are the three delimiters, so translate them all to blanks and then split into the two digit strings
        spl=s.replace(".", " ").replace("#", " ").split()
        if len(spl) != 2:
            return None, None
        try:
            return int(spl[0]), int(spl[1])
        except:
            return None, None

        # =============================================================================
        # Format the Vol/Num/Whole information


    def FormatSerialForSorting(self) -> str:
        if self.Whole is not None and self.Vol is not None and self.Num is not None:
            return "#"+"{0:7.2f}".format(self.Whole)+"  (V"+"{0:7.2f}".format(self.Vol)+"#"+"{0:7.2f}".format(self.Num)+")"+self.NumSuffix

        if self.Whole is not None:
            return "#"+"{0:7.2f}".format(self.Whole)+self._WSuffix

        if self.Vol is None and self.Num is None:
            return "0000.00"

        v="0000.00"
        n="0000.00"
        if self.Vol is not None:
            v="{0:7.2f}".format(self.Vol)
        if self.Num is not None:
            n="{0:7.2f}".format(self.Num)

        return "V"+v+"#"+n+self.NumSuffix

        # =============================================================================================
        # Try to interpret a complex string as serial information
        # If there's a trailing Vol+Num designation at the end of a string, interpret it.

        # We accept:
        #       ...Vnn[,][ ]#nnn[ ]
        #       ...nnn nnn/nnn      a number followed by a fraction
        #       ...nnn/nnn[  ]      vol/num
        #       ...rrr/nnn          vol (in Roman numerals)/num
        #       ...nn.mm
        #       ...nn[ ]


    def InterpretSerial(self, s: str):
        self.Vol=None
        self.Num=None
        self.Whole=None
        self.Suffix=None

        s=s.upper()

        # First look for a Vol+Num designation: Vnnn #mmm
        p=re.compile("^.*"+  # Leading stuff
                     "V([0-9]+),?\s*"+  # Vnnn + optional comma + optional whitespace
                     "#([0-9]+)([a-zA-Z]?)"  # # #nnn + optional single alphabetic character suffix
                     "\s*$")  # optional whitespace
        m=p.match(s)
        if m is not None and len(m.groups()) in [2, 3]:
            self.Vol=int(m.groups()[0])
            self.Num=int(m.groups()[1])
            if len(m.groups()) == 3:
                self.Suffix=m.groups()[2]
            return self

        p=re.compile("^.*"+  # Leading stuff
                     "V[oO][lL]\s*([0-9]+),?\s*"+  # Vol (or VOL) + optional space + nnn + optional comma + optional space
                     "#([0-9]+)([a-zA-Z]?)"  # + #nnn + optional single alphabetic character suffix
                     "\s*$")  # optional whitespace
        m=p.match(s)
        if m is not None and len(m.groups()) in [2, 3]:
            self.Vol=int(m.groups()[0])
            self.Num=int(m.groups()[1])
            if len(m.groups()) == 3:
                self.Suffix=m.groups()[2]
            return self

        # Now look for nnn nnn/nnn (fractions!)
        p=re.compile("^.*?([0-9]+)\s+([0-9]+)/([0-9]+)\s*$")  # Leading stuff + nnn + mandatory whitespace + nnn + slash + nnn * optional whitespace
        m=p.match(s)
        if m is not None and len(m.groups()) == 3:
            self.Whole=int(m.groups()[0])+int(m.groups()[1])/int(m.groups()[2])
            return self

        # Now look for nnn/nnn (which is understood as vol/num
        p=re.compile("^.*?([0-9]+)/([0-9]+)\s*$")  # Leading stuff + nnn + slash + nnn * optional whitespace
        m=p.match(s)
        if m is not None and len(m.groups()) == 2:
            self.Vol=int(m.groups()[0])
            self.Num=int(m.groups()[1])
            return self

        # Now look for xxx/nnn, where xxx is in Roman numerals
        p=re.compile("^\s*([IVXLC]+)/([0-9]+)\s*$")  # Leading whitespace + roman numeral characters + slash + nnn + whitespace
        m=p.match(s)
        if m is not None and len(m.groups()) == 2:
            self.Vol=roman.fromRoman(m.groups()[0])
            self.Num=int(m.groups()[1])
            return self

        # Next look for nnn-nnn (which is a range of issue numbers; only the start is returned)
        p=re.compile("^.*?([0-9]+)-([0-9]+)\s*$")  # Leading stuff + nnn + dash + nnn * optional whitespace
        m=p.match(s)
        if m is not None and len(m.groups()) == 2:
            self.Whole=int(m.groups()[0])
            return self

        # Now look for a trailing decimal number
        p=re.compile("^.*?([0-9]+\.[0-9]+)\s*$")  # Leading characters + single non-digit + nnn + dot + nnn + whitespace
        # the ? makes * a non-greedy quantifier
        m=p.match(s)
        if m is not None and len(m.groups()) == 1:
            self.Vol=None
            self.Num=float(m.groups()[0])
            return self

        # Now look for a single trailing number
        p=re.compile("^.*?([0-9]+)([a-zA-Z]?)\s*$")  # Leading stuff + nnn + optional single alphabetic character suffix + whitespace
        m=p.match(s)
        if m is not None and len(m.groups()) in [1, 2]:
            self.Vol=None
            self.Num=int(m.groups()[0])
            if len(m.groups()) == 2:
                self.Suffix=m.groups()[1]
            return self

        # Now look for trailing Roman numerals
        p=re.compile("^.*?\s+([IVXLC]+)\s*$")  # Leading stuff + mandatory whitespace + roman numeral characters + optional trailing whitespace
        m=p.match(s)
        if m is not None and len(m.groups()) == 1:
            self.Num=roman.fromRoman(m.groups()[0])
            return self

        # No good, return failure
        return self

#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
class FanzineIssueSpec:

    def __init__(self, Vol=None, Num=None, NumSuffix=None, Whole=None, WSuffix=None, Year=None, Month=None, MonthText=None, Day=None, DayText=None):
        self._FS=FanzineSerial(Vol=Vol, Num=Num, NumSuffix=NumSuffix, Whole=Whole, WSuffix=WSuffix)
        self._FD=FanzineDate(Year=Year, Month=Month, MonthText=MonthText, Day=Day, DayText=DayText)
        #self.UninterpretableText=None   # Ok, I give up.  Just hold the text as text.
        #self.TrailingGarbage=None       # The uninterpretable stuff following the interpretable spec held in this instance

    # Two issue designations are deemed to be equal if they are identical or if the VN matches while at least on of the Wholes in None or
    # is the Whole matches and at least one of the Vs and Ns is None.  (We would allow match of (W13, V3, N2) with (W13), etc.)
    def __IssueEQ__(self, other: FanzineIssueSpec) -> bool:
        return self._FS == other._FS

    def __DateEq__(self, other: FanzineIssueSpec) -> bool:
        return self._FD == other._FD

    # Class equality check.
    def __eq__(self, other: FanzineIssueSpec):
        return self._FS == other._FS and self._FD == other._FD

    def __ne__(self, other: FanzineIssueSpec):
        return not self.__eq__(other)

    #-----------------------------
    # Define < operator for sorting
    def __lt__(self, other: FanzineIssueSpec) -> bool:
        if other is None:
            return False
        if self._FD is not None and other._FD is not None:
            return self._FD < other._FD
        if self._FS is not None and other._FS is not None:
            return self._FS < other._FS
        return False

    def Copy(self, other: FanzineIssueSpec):
        self._FD=other._FD
        self._FS=other._FS
        self._UninterpretableText=other._UninterpretableText
        self._TrailingGarbage=other._TrailingGarbage

    # .....................
    @property
    def Vol(self) -> Optional[int]:
        return self._FS.Vol

    @Vol.setter
    def Vol(self, val: Optional[int, str]):
        self._FS.Vol=ToNumeric(val)

    # .....................
    @property
    def Num(self) -> Optional[int]:
        return self._FS.Num

    @Num.setter
    def Num(self, val: Optional[int, str]):
        self._FS.Num=ToNumeric(val)

    # .....................
    @property
    def NumSuffix(self) -> Optional[str]:
        return self._FS.NumSuffix

    @NumSuffix.setter
    def NumSuffix(self, val: Optional[str]):
        self._FS.NumSuffix=val

    #.....................
    @property
    def Whole(self) -> Optional[int]:
        return self._FS.Whole

    @Whole.setter
    def Whole(self, val: Optional[int, str]):
        self._FS.Whole=ToNumeric(val)

    # .....................
    @property
    def WSuffix(self) -> Optional[str]:
        return self._FS.WSuffix

    @WSuffix.setter
    def WSuffix(self, val: Optional[str]):
        self._FS.WSuffix=val

    #.....................
    @property
    def Year(self) -> Optional[int]:
        return self._FD.Year

    @Year.setter
    def Year(self, val: Optional[int, str]):
        self._FS.Year=val

    #.....................
    # This is a non-settable property -- it is always derived from the numeric Year
    @property
    def YearText(self) -> Optional[str]:
        return self._FD.YearText

    #.....................
    @property
    def Month(self) ->Optional[int]:
        return self._FD.Month

    @Month.setter
    def Month(self, val: Optional[int, str]):
        self._FS.Month=val

    #.....................
    @property
    def MonthText(self) -> Optional[str]:
        return self._FD.MonthText

    @MonthText.setter
    def MonthText(self, val: Optional[str]):
        self._FD.MonthText=val

    #.....................
    @property
    def Day(self) -> Optional[int]:
        return self._FD.Day

    @Day.setter
    def Day(self, val: Optional[int]):
        self._FD.Day=val

    # .....................
    @property
    def DayText(self) -> Optional[str]:
        return self._FD.DayText

    @DayText.setter
    def DayText(self, val: Optional[str]):
        self._FD._DayText=val

    # #.....................
    # @property
    # def UninterpretableText(self) -> Optional[str]:
    #     return self._UninterpretableText
    #
    # @UninterpretableText.setter
    # def UninterpretableText(self, val: Optional[str]):
    #     if val is None:
    #         self._UninterpretableText=None
    #         return
    #     val=val.strip()
    #     if len(val) == 0:
    #         self._UninterpretableText=None
    #         return
    #     self._UninterpretableText=val
    #
    # #.....................
    # @property
    # def TrailingGarbage(self) ->Optional[str]:
    #     return self._TrailingGarbage
    #
    # @TrailingGarbage.setter
    # def TrailingGarbage(self, val: Optional[str]):
    #     if val is None:
    #         self._TrailingGarbage=None
    #         return
    #     val=val.strip()
    #     if len(val) == 0:
    #         self._TrailingGarbage=None
    #         return
    #     self._TrailingGarbage=val

    #.....................
    @property
    def Date(self) -> str:
        return self._FD.Date

    @property
    def Serial(self) -> str:
        return self._FS.Serial

    # .....................
    # Return a datetime object
    def Datetime(self) -> datetime:
        return self._FD.Datetime

    # .....................
    def SetWhole(self, num: int, suffix: str):
        self._FS.SetWhole(num, suffix)

    # .....................
    def SetDate(self, y: int, m: int):
        self._FD.SetDate(y, m)

    #.......................
    # Convert the FanzineIssueSpec into a debugging form
    def DebugStr(self) -> str:
        # if self.UninterpretableText is not None:
        #     return "IS("+self.UninterpretableText+")"

        s="IS("+self._FS.DebugStr()+" "+self._FD.DebugStr()
        # if self.TrailingGarbage is not None:
        #     s=s+", TG='"+self.TrailingGarbage+"'"
        # if self.UninterpretableText is not None:
        #     s=s+", UT='"+self.UninterpretableText+"'"
        s=s+")"

        return s

    #.......................
    def IsEmpty(self) -> bool:
        return self._FD.IsEmpty() and self._FS.IsEmpty()

    #.......................
    # Convert the FanzineIssueSpec into a pretty string for display or printing
    def __str__(self):
        # if self.UninterpretableText is not None:
        #     return self.UninterpretableText.strip()

        tg=""
        # if self.TrailingGarbage is not None:
        #     tg=" "+self.TrailingGarbage

        if not self._FD.IsEmpty():
            tg+=" "+str(self._FD)

        if not self._FS.IsEmpty():
            tg+=" "+str(self._FS)

        return tg.strip()

    # =====================================================================================
    def DecodeIssueDesignation(self, s: str):
        self._FS.DecodeIssueDesignation(s)


    #=============================================================================
    def FormatYearMonthForSorting(self):
        return self._FD.FormatYearMonthForSorting()

    #=============================================================================
    # Format the Vol/Num/Whole information
    def FormatSerialForSorting(self):
        return self._FS.FormatSerialForSorting()

######################################################################################################################
######################################################################################################################
# Now define class FanzineIssueSpecList
######################################################################################################################
######################################################################################################################
# A Fanzine issue spec list contains the information to handle a list of issues of a single fanzine.
# It includes the series name, editors(s), and a list of Fanzine Issue specs.
#TODO: This can be profitably extended by changing the ISL class to include specific names and editors for each issue, since sometimes
#TODO: a series does not have a consistent set throughout.

class FanzineIssueSpecList:
    def __init__(self, List: Optional[List[FanzineIssueSpec]]=None):
        self._List=List  # Use setter

    def AppendIS(self, fanzineIssueSpec: FanzineIssueSpec):
        if isinstance(fanzineIssueSpec, FanzineIssueSpec):
            self._List.append(fanzineIssueSpec)
        elif isinstance(fanzineIssueSpec, FanzineIssueSpecList):
            self._List.extend(fanzineIssueSpec.List)
        elif fanzineIssueSpec is None:
            return
        else:
            print("****FanzineIssueSpecList.AppendIS() had strange input")
        return

    def Extend(self, isl: FanzineIssueSpecList) -> FanzineIssueSpecList:
        self._List.extend(isl)
        return self

    def DebugStr(self) -> str:
        s=""
        for i in self._list:
            if len(s) > 0:
                s=s+",  "
            if i is not None:
                s=s+i.DebugStr()
            else:
                s=s+"Missing ISList"
        if len(s) == 0:
            s="Empty ISlist"
        return s

    def __str__(self):   # Format the ISL for pretty
        s=""
        for i in self._list:
            if i is not None:
                if len(s) > 0:
                    s=s+", "
                s=s+str(i)
        return s

    def __len__(self):
        return len(self._list)

    @property
    def List(self) -> FanzineIssueSpecList:
        return self._list

    @List.setter
    def List(self, val: Optional[FanzineIssueSpec, FanzineIssueSpecList]):
        if val is None:
            self._list=[]
            return
        if isinstance(val, FanzineIssueSpec):
            self._list=[val]
            return
        if isinstance(val, FanzineIssueSpecList):
            self._list=val.List
        print("****FanzineIssueSpecList.List setter() had strange input")

    @List.getter
    def List(self) -> FanzineIssueSpecList:
        return self._list

    def __getitem__(self, key: int) -> FanzineIssueSpec:
        return self._list[key]

    def __setitem__(self, key: int, value: FanzineIssueSpec):
        self._list[key]=value
        return self


######################################################################################################################
######################################################################################################################
# Stand-alone functions
######################################################################################################################
#####################################################################################################################

# Format an integer month as text
def MonthName(month: int, short=False) -> str:
    if month is None:
        return ""

    if 0 < month < 13:
        if short:
            m=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month-1]  # -1 is to deal with zero-based indexing...
        else:
            m=["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"][month-1]  # -1 is to deal with zero-based indexing...
    else:
        m="<invalid: "+str(month)+">"
    return m


# ==============================================================================
# Format an integer day as text
def DayName(day: int) -> str:
    if day is None or day == 0:
        return ""

    if day < 1 or day > 31:
        return "<invalid day="+str(day)+">"

    return str(day)

# =============================================================================
# Format an integer year as text.  Note that this is designed for fanzines, so two-digit years become ambiguous at 2033.
def YearName(year: Optional[int, str]) -> str:
    if year is None or year == 0:
        return ""
    return str(YearAs4Digits(year))

# ====================================================================================
#  Handle dates like "Thanksgiving"
# Returns a month/day tuple which will often be exactly correct and rarely off by enough to matter
# Note that we don't (currently) attempt to handle moveable feasts by taking the year in account
def InterpretNamedDay(dayString: str) -> Optional[Tuple[int, int]]:
    namedDayConverstionTable={
        "unknown": (None, None),
        "unknown ?": (None, None),
        "new year's day": (1, 1),
        "edgar allen poe's birthday": (1, 19),
        "edgar allan poe's birthday": (1, 19),
        "edgar alan poe's birthday": (1, 19),
        "groundhog day": (2, 4),
        "daniel yergin day": (2, 6),
        "canadian national flag day": (2, 15),
        "national flag day": (2, 15),
        "chinese new year": (2, 15),
        "lunar new year": (2, 15),
        "leap day": (2, 29),
        "ides of march": (3, 15),
        "st urho's day": (3, 16),
        "st. urho's day": (3, 16),
        "saint urho's day": (3, 16),
        "april fool's day": (4, 1),
        "good friday": (4, 8),
        "easter": (4, 10),
        "national garlic day": (4, 19),
        "world free press day": (5, 3),
        "cinco de mayo": (5, 5),
        "victoria day": (5, 22),
        "world no tobacco day": (5, 31),
        "world environment day": (6, 5),
        "great flood": (6, 19),  # Opuntia, 2013 Calgary floods
        "summer solstice": (6, 21),
        "world wide party": (6, 21),
        "canada day": (7, 1),
        "stampede": (7, 10),
        "stampede rodeo": (7, 10),
        "stampede parade": (7, 10),
        "system administrator appreciation day": (7, 25),
        "apres le deluge": (8, 1),  # Opuntia, 2013 Calgary floods
        "august 14 to 16": (8, 15),
        "international whale shark day": (8, 30),
        "labor day": (9, 3),
        "labour day": (9, 3),
        "september 15 to 18": (9, 17),
        "september 17 to 20": (9, 19),
        "(canadian) thanksgiving": (10, 15),
        "halloween": (10, 31),
        "october (halloween)": (10, 31),
        "remembrance day": (11, 11),
        "rememberance day": (11, 11),
        "thanksgiving": (11, 24),
        "november (december)": (12, None),
        "before christmas december": (12, 15),
        "saturnalia": (12, 21),
        "winter solstice": (12, 21),
        "christmas": (12, 25),
        "christmas issue": (12, 25),
        "christmas issue december": (12, 25),
        "xmas ish the end of december": (12, 25),
        "boxing day": (12, 26),
        "hogmanay": (12, 31),
        "auld lang syne": (12, 31),
    }
    try:
        return namedDayConverstionTable[dayString.lower()]
    except:
        return None


# ====================================================================================
# Deal with situations like "late December"
# We replace the vague relative term by a non-vague (albeit unreasonably precise) number
def InterpretRelativeWords(daystring: str) -> Optional[int]:
    conversionTable={
        "start of": 1,
        "early": 7,
        "early in": 7,
        "mid": 15,
        "middle": 15,
        "?": 15,
        "middle late": 19,
        "late": 24,
        "end of": 30,
        "the end of": 30,
        "around the end of": 30
    }

    try:
        return conversionTable[daystring.replace(",", " ").replace("-", " ").lower()]
    except:
        return None


# =============================================================================
# Take various text versions of a month and convert them to the full-out spelling
def StandardizeMonth(month: str) -> str:
    table={"1": "January", "jan": "January",
           "2": "February", "feb": "February",
           "3": "March", "mar": "March",
           "4": "April", "apr": "April",
           "5": "May",
           "6": "June", "jun": "June",
           "7": "July", "jul": "july",
           "8": "August", "aug": "August",
           "9": "September", "sep": "September",
           "10": "October", "oct": "October",
           "11": "November", "nov": "November",
           "12": "December", "dec": "December"}

    if month.lower().strip() not in table.keys():
        return month

    return table[month.lower().strip()]


# =================================================================================
# Convert 2-digit years to four digit years
# We accept 2-digit years from 1933 to 2032
def YearAs4Digits(year: Optional[int, str]) -> Optional[int]:
    if year is None:
        return None
    if isinstance(year, str):
        try:
            year=int(year)
        except:
            return year
    if year > 100:
        return year
    if year < 33:
        return year+2000
    return year+1900


# =================================================================================
# Turn year into an int
def InterpretYear(yearText: Optional[int, str]) -> Optional[int, str]:

    if yearText is None:
        return None
    if isinstance(yearText, int):  # If it's already an int, not to worry
        return yearText
    if len(yearText.strip()) == 0:  # If it's blank, return 0
        return None

    yearText=RemoveHTMLDebris(yearText)  # We treat <br> and </br> as whitespace, also
    if len(yearText) == 0:
        return None

    # Drop trailing question mark(s)
    if yearText[-1] == "?":
        yearText=yearText[:-1]
    if yearText[-1] == "?":
        yearText=yearText[:-1]

    # Convert to int
    try:
        return YearAs4Digits(int(yearText))
    except:
        # OK, that failed. Could it be because it's something like '1953-54'?
        try:
            if '-' in yearText:
                years=yearText.split("-")
                if len(years) == 2:
                    y1=YearAs4Digits(int(years[0]))
                    y2=YearAs4Digits(int(years[1]))
                    return max(y1, y2)
        except:
            pass

    Log("   ***Year conversion failed: '"+yearText+"'", isError=True)
    return None


# =================================================================================
# Turn day into an int
def InterpretDay(dayData: Optional[int, str]) -> Optional[int]:

    if dayData is None:
        return None
    if isinstance(dayData, int):  # If it's already an int, not to worry
        return dayData
    if len(dayData.strip()) == 0:  # If it's blank, return 0
        return None

    # Convert to int
    dayData=RemoveHTMLDebris(dayData)
    if len(dayData) == 0:
        return None
    try:
        day=int(dayData)
    except:
        Log("   ***Day conversion failed: '"+dayData+"'", isError=True)
        day=None
    return day


# =================================================================================
# Make sure day is within month
def BoundDay(dayInt: Optional[int], monthInt: Optional[int]) -> Optional[int]:
    if dayInt is None:
        return None
    if monthInt is None:    # Should never happen!
        return dayInt
    if dayInt < 1:
        return 1
    if monthInt == 2 and dayInt > 28:   #This messes up leap years. De minimus
        return 28
    if monthInt in [4, 6, 9, 11] and dayInt > 30:
        return 30
    if monthInt in [1, 3, 5, 7, 8, 10, 12] and dayInt > 31:
        return 31
    return dayInt


# =================================================================================
# Deal with things of the form "June 20," and "20 June" and just "June"
# Return a tuple of (month, day)
# (Day defaults to 1 if no day was supplied.)
def InterpretMonthDay(s: str) -> Optional[Tuple[int, int]]:
    s=s.strip() # Get rid of leading and traling blanks as they can't possibly be of interest
    if s[-1] == ",":    # Get rid of trailing comma
        s=s[:-1]
    s=s.replace("    ", " ").replace("   ", " ").replace("  ", " ") # Turn runs of up to 24 spaces into a single space

    # We now handle three cases:
    #       <month> <day> (A month name followed by a space followed by a day number)
    #       <day> <month>
    #       <month>
    pieces=s.split(" ")
    if len(pieces) == 1:
        m=MonthNameToInt(pieces[0])
        if m is not None:
            return m, 1

    # Ok, we know that there are at least two pieces
    if len(pieces) > 2:     # Currently uninterpretable
        return None

    m=MonthNameToInt(pieces[0])
    if m is not None and IsInt(pieces[1]):
        return m, int(pieces[1])

    m=MonthNameToInt(pieces[1])
    if m is not None and IsInt(pieces[0]):
        return m, int(pieces[0])

    return None


# =================================================================================
# If necessary, turn text month into an int
def InterpretMonth(monthData: Optional[str, int]) -> Optional[int]:

    if monthData is None:
        return None
    if isinstance(monthData, int):
        return monthData
    if len(monthData.strip()) == 0:  # If it's blank, return 0
        return None

    monthData=RemoveHTMLDebris(monthData)
    if len(monthData) == 0:
        return None

    return MonthNameToInt(monthData)


# ====================================================================================
# Convert a text month to integer
def MonthNameToInt(text: str) -> Optional[int]:
    monthConversionTable={"jan": 1, "january": 1, "1": 1,
                          "feb": 2, "february": 2, "feburary": 2, "2": 2,
                          "mar": 3, "march": 3, "3": 3,
                          "apr": 4, "april": 4, "4": 4,
                          "may": 5, "5": 5,
                          "jun": 6, "june": 6, "6": 6,
                          "jul": 7, "july": 7, "7": 7,
                          "aug": 8, "august": 8, "8": 8,
                          "sep": 9, "sept": 9, "september": 9, "9": 9,
                          "oct": 10, "october": 10, "10": 10,
                          "nov": 11, "november": 11, "11": 11,
                          "dec": 12, "december": 12, "12": 12,
                          "1q": 1, "q1": 1,
                          "4q": 4, "q2": 4, "2q": 4,
                          "7q": 7, "q3": 7, "3q": 7,    # 4q, 7q, 10q is for some fapazines which are numbered by an odd mix of quarter and month.
                          "10q": 10, "q4": 10,
                          "spring": 4, "spr": 4,
                          "summer": 7, "sum": 7,
                          "fall": 10, "autumn": 10, "fal": 10,
                          "winter": 1, "win": 1,
                          "xmas": 12, "christmas": 12}

    text=text.replace(" ", "").lower()

    # First look to see if the input is two month names separated by a non-alphabetic character (e.g., "September-November"
    m=re.compile("^([a-zA-Z]+)[-/]([a-zA-Z]+)$").match(text)
    if m is not None and len(m.groups()) == 2 and len(m.groups()[0]) > 0:
        m1=MonthNameToInt(m.groups()[0])
        m2=MonthNameToInt(m.groups()[1])
        if m1 is not None and m2 is not None:
            return math.ceil((m1+m2)/2)

    try:
        return monthConversionTable[text]
    except:
        return None


# ====================================================================================
# Deal with completely random date strings that we've uncovered and added
# There's no rhyme nor reason here -- just otherwise uninterpretable things we've run across.
def InterpretRandomDatestring(text: str) -> Optional[FanzineDate]:
    text=text.lower()
    if text == "solar eclipse 2017":
        return FanzineDate(Year=2017, Month=8, DayText="Solar Eclipse", Day=21)
    if text == "2018 new year's day":
        return FanzineDate(Year=2018, Month=1, DayText="New Years Day", Day=1)
    if text == "christmas 2015.":
        return FanzineDate(Year=2015, Month=12, DayText="Christmas", Day=25)
    if text == "hogmanay 1991/1992":
        return FanzineDate(Year=1991, Month=12, DayText="Hogmany", Day=31)
    if text == "grey cup day 2014":
        return FanzineDate(Year=2014, Month=11, DayText="Grey Cup Day", Day=11)
    if text == "october 2013, halloween":
        return FanzineDate(Year=2013, Month=10, DayText="Halloween", Day=31)
    if text == "stampede parade day 2019":
        return FanzineDate(Year=2019, Month=7, DayText="Stampede Parade Day", Day=5)

    return None

# =============================================================================
# Sometimes we don't have raw text for the whole date, but do have raw text for the month and day.
# Use them to generate raw text for the date
def CreateRawText(dayText: str, monthText: str, yearText: str) -> str:

    # First make sure we have the text or an empty string if the item is None
    mo=monthText.strip() if monthText is not None else ""
    da=dayText.strip() if dayText is not None else ""
    ye=yearText.strip() if yearText is not None else ""

    # The format depends on what's known and what's not, and also depends on wether the month and day representations are strings of numbers ("7") or include other characters ("July")
    if IsNumeric(mo) and IsNumeric(da):
        return mo+"/"+da+"/"+ye             # 7/4/1776
    elif not IsNumeric(mo) and IsNumeric(da):
        return mo+" "+da+", "+ye            # July 4, 1776
    elif IsNumeric(mo) and da == "":
        return MonthName(int(mo))+" "+ye    # July 1776
    else:
        # Text month and day.
        return (mo+" ").lstrip()+(da+" ").lstrip()+ye  # The lstrip() gets rid of the extra space if mo or da is null


#==============================================================================
# Given the contents of various table columns, attempt to extract serial information
# This uses InterpretSerial for detailed decoding
def ExtractSerialNumber(volText: str, numText: str, wholeText: str, volNumText: str, titleText: str) -> FanzineSerial:
    wholeInt=None
    volInt=None
    numInt=None
    maybeWholeInt=None
    suffix=None

    if wholeText is not None:
        wholeInt=InterpretNumber(wholeText)

    if volNumText is not None:
        ser=FanzineSerial().InterpretSerial(volNumText)
        if ser.Vol is not None and ser.Num is not None:  # Otherwise, we don't actually have a volume+number
            volInt=ser.Vol
            numInt=ser.Num
            suffix=ser.Suffix

    if volText is not None:
        volInt=InterpretNumber(volText)

    # If there's no vol, anything under "Num", etc., must actually be a whole number
    if volText is None:
        try:
            maybeWholeText=numText
            maybeWholeInt=int(maybeWholeText)
            numText=None
        except:
            pass

    # But if the *is* a volume specified, than any number not labelled "whole" must be a number within the volume
    if volText is not None and numText is not None:
        numInt=InterpretNumber(numText)

    # OK, now figure out the vol, num and whole.
    # First, if a Vol is present, and an unambigious num is absent, the an ambigious Num must be the Vol's num
    if volInt is not None and numInt is None and maybeWholeInt is not None:
        numInt=maybeWholeInt
        maybeWholeInt=None

    # If the wholeInt is missing and maybeWholeInt hasn't been used up, make it the wholeInt
    if wholeInt is None and maybeWholeInt is not None:
        wholeInt=maybeWholeInt
        maybeWholeInt=None

    # Next, look at the title -- titles often have a serial designation at their end.

    if titleText is not None:
        # Possible formats:
        #   n   -- a whole number
        #   n.m -- a decimal number
        #   Vn  -- a volume number, but where's the issue?
        #   Vn[,] #m  -- a volume and number-within-volume
        #   Vn.m -- ditto
        ser=FanzineSerial().InterpretSerial(titleText if type(titleText) is not list else titleText[0])

        # Some indexes have fanzine names ending in <month> <year>.  We'll detect these by looking for a trailing number between 1930 and 2050, and reject
        # getting vol/ser, etc., from the title if we find it.
        if ser.Num is None or ser.Num < 1930 or ser.Num > 2050:

            if ser.Vol is not None and ser.Num is not None:
                if volInt is None:
                    volInt=ser.Vol
                if numInt is None:
                    numInt=ser.Num

                if volInt != ser.Vol:
                    Log("***Inconsistent serial designations: Volume='"+str(volInt)+"' which is not Vol='"+str(ser.Vol)+"'", isError=True)
                if numInt != ser.Num:
                    Log("***Inconsistent serial designations: Number='"+str(numInt)+"' which is not Num='"+str(ser.Num)+"'", isError=True)

            elif ser.Num is not None:
                if wholeInt is None:
                    wholeInt=ser.Num

                if wholeInt != ser.Num:
                    Log("***Inconsistent serial designations: Whole='"+str(wholeInt)+"'  which is not Num='"+str(ser.Num)+"'", isError=True)

            if ser.Whole is not None:
                wholeInt=ser.Whole

            suffix=ser.Suffix

    return FanzineSerial(Vol=volInt, Num=numInt, Whole=wholeInt, WSuffix=suffix)