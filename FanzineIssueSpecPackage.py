# A FanzineIssueSpec contains the information for one fanzine issue's specification, e.g.:
#  V1#2, #3, #2a, Dec 1967, etc.
# It can be a volume+number or a whole numer or a date. (It can be more than one of these, also, and all are retained.)
from __future__ import annotations

import math
import re
from typing import Union, Tuple, Optional, List
from contextlib import suppress

from functools import reduce
import datetime
from dateutil import parser

from Log import Log
from HelpersPackage import ToNumeric, IsNumeric, IsInt, Int
from HelpersPackage import RemoveHTMLDebris
from HelpersPackage import InterpretNumber, InterpretRoman
from HelpersPackage import CaseInsensitiveCompare
from HelpersPackage import CanonicizeColumnHeaders

class FanzineDate:
    def __init__(self,
                 Year: Union[int, str, None]=None,
                 Month: Union[int, str, Tuple[int, str], None]=None,
                 MonthText: Optional[str]=None,
                 Day: Union[int, str, Tuple[int, str], None]=None,
                 DayText: Optional[str]=None,
                 MonthDayText: Optional[str] =None) -> None:
        self.Year=Year

        self._Month=None
        self._MonthText=None
        if type(Month) is not tuple and MonthText is not None:
            Month=(Month, MonthText)
        self.Month=Month
        if Month is None and MonthText is not None:
            self.Month=InterpretMonth(MonthText)        # If only Monthtext is defined, use it to calculate Month

        self._Day=None
        self._DayText=None
        if type(Day) is tuple:
            self.Day=Day
        elif Day is not None and DayText is not None:
            self.Day=(Day, DayText)
        elif Day is not None and DayText is None:
            self.Day=Day
        elif Day is None and DayText is not None:        # If only DayText is defined, use it to calculate Day
            self.Day=InterpretDay(DayText)

        self._MonthDayText=MonthDayText                 # Overrides display of both month and day, but has no other effect

        self._LongDates=False

        #TODO: Where do these two go?
        #self.UninterpretableText=None  # Ok, I give up.  Just hold the text as text.
        #self.TrailingGarbage=None  # The uninterpretable stuff following the interpretable spec held in this instance

    def __eq__(self, other: FanzineDate) -> bool:               # FanzineDate
        # Empty dates are equal
        if (self is None and other is None) or (self.IsEmpty() and other.IsEmpty()):
            return True
        # If we're checking a non-None FanzineDate against a null input, it's not equal
        if other is None:
            return False
        # If either date is entirely None, it's not equal
        if self._Year is None and self._Month is None and self._Day is None:
            return False
        if other._Year is None and other._Month is None and other._Day is None:
            return False
        # OK, we know that both self and other have a non-None date element, so just check for equality
        return self._Year == other._Year and self._Month == other._Month and self._Day == other._Day

    def __ne__(self, other: FanzineDate) -> bool:               # FanzineDate
        return not self.__eq__(other)

    # -----------------------------
    # Define < operator for sorting
    def __lt__(self, other: FanzineDate) -> bool:               # FanzineDate
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

    def Copy(self, other: FanzineDate) -> None:               # FanzineDate
        self._Year=other._Year
        self._Month=other._Month
        self._MonthText=other._MonthText
        self._Day=other._Day
        self._DayText=other._DayText
        self._MonthDayText=other._MonthDayText
        self._LongDates=other._LongDates        # Used only to coerce the __str__ to use long dates one time only
        #self._UninterpretableText=other._UninterpretableText
        #self._TrailingGarbage=other._TrailingGarbage

    # .....................
    @property
    def LongDates(self):               # FanzineDate
        self._LongDates=True        # Set _LongDates to True.  The next use of __str__() will set it back to False
        return self                 # This was str(FD) will yield short dates and str(FD.LongDates) will yield long dates

    # .....................
    @property
    def Year(self) -> int:               # FanzineDate
        return self._Year

    @Year.setter
    def Year(self, val: Union[int, str]) -> None:               # FanzineDate
        if isinstance(val, str):
            self._Year=ToNumeric(YearAs4Digits(val))
        else:
            self._Year=YearAs4Digits(val)

    # .....................
    # This is a non-settable property -- it is always derived from the numeric Year
    @property
    def YearText(self) -> str:               # FanzineDate
        return YearName(self._Year)

    # .....................
    @property
    def Month(self) -> int:               # FanzineDate
        return self._Month

    @Month.setter
    def Month(self, val: Union[int, str, Tuple[int, str]]) -> None:               # FanzineDate
        if isinstance(val, str):
            self._Month=InterpretMonth(val)     # If you supply only the MonthText, the Month number is computed
            self._MonthText=val if (val is not None and len(val) > 0) else None
        elif isinstance(val, Tuple):    # Use the Tuple to set both Month and MonthText
            self._Month=val[0]
            self._MonthText=val[1] if (val[1] is not None and len(val) > 0) else None
        else:
            self._Month=val
            self._MonthText=None  # If we set a numeric month, any text month gets blown away as no longer relevant

    # .....................
    @property
    def MonthText(self) -> str:               # FanzineDate
        if self._MonthText is not None:
            return self._MonthText
        if self._Month is not None:
            return MonthName(self._Month)
        return ""
    # There is no MonthText setter -- to set it use the init or the Month setter

    # .....................
    @property
    def Day(self) -> int:               # FanzineDate
        return self._Day

    @Day.setter
    def Day(self, val: Union[int, str, Tuple[int, str]]) -> None:               # FanzineDate
        if isinstance(val, str):    # If you supply only the DayText, the Day number is computed
            self._Day=ToNumeric(val) if (val is not None and len(val) > 0) else None
            self._DayText=val if (val is not None and len(val) > 0) else None
        elif isinstance(val, Tuple):    # Use the Tuple to set both Day and DayText
            self._Day=val[0]
            self._DayText=val[1] if (val[1] is not None  and len(val) > 0) else None
        else:
            self._Day=val
            self._DayText=None  # If we set a numeric day, any day text gets blown away as no longer relevant

    # .....................
    @property
    def DayText(self) -> Union[str, None]:               # FanzineDate
        if self._DayText is not None:
            return self._DayText
        if self._Day is not None:
            return DayName(self._Day)
        return None
    # There is no DayText setter -- to set it use the init or the Day setter

    # .....................
    @property
    def MonthDayText(self):
        return self._MonthDayText

    @MonthDayText.setter
    def MonthDayText(self,val):
        self._MonthDayText=val

    # .....................
    @property
    def Date(self) -> Optional[datetime.date]:               # FanzineDate
        if self.IsEmpty():
            return None
        y=self._Year if self._Year is not None else 1
        m=self._Month if self._Month is not None else 1
        d=self._Day if self._Day is not None else 1
        return datetime.date(y, m, d)


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


    # .......................
    # Convert the FanzineIssueSpec into a debugging form
    def DebugStr(self) -> str:               # FanzineDate
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
        if self.MonthDayText is not None:
            d=d+":::"+self.MonthDayText
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
    def IsEmpty(self) -> bool:               # FanzineDate
        return not reduce(lambda a, b: a or b, [self._DayText, self._Day, self._MonthText, self._Month, self._Year])

    # .......................
    # Convert the FanzineIssueSpec into a pretty string for display or printing
    def __str__(self) -> str:               # FanzineDate
        #if self.UninterpretableText is not None:
        #    return self.UninterpretableText.strip()

        tg=""
        #if self.TrailingGarbage is not None:
        #    tg=" "+self.TrailingGarbage

        # y, m, d will be None if there is no data; yt, mt, dt will contain the display text or ""
        y=self.Year
        yt=str(y) if y is not None else ""

        m=self.Month
        mt=""
        if m is not None:
            mt=MonthName(m, short=not self._LongDates) if m is not None else None
        self._LongDates=False       # LongDates only stays set for a single use of str()
        if self._MonthText is not None:
            mt=self._MonthText
            m=0

        d=self.Day
        dt=str(d) if d is not None else ""
        if self._DayText is not None:
            dt=self._DayText
            d=0

        # If DayText is "Early", "Mid" or "Late", or such-like we attach it to the front of the month
        if dt is not None:
            if dt in ["Early", "Mid", "Middle", "Late"]:
                mt=dt+" "+mt
                dt=""
                d=None

        # But if MonthDayText is defined, it overrides both the month and the day as far as display goes. (It replaces the month and the day is set to None)
        if self._MonthDayText is not None:
            mt=self._MonthDayText
            m=0     # This value is only here to trigger display of the revised mt
            d=None
            dt=None


        # We don't treat a day without a month and year or a month without a year as valid and printable
        if y is not None and m is not None and d is not None:
            return mt +" "+dt+", "+yt
        if y is not None and m is not None and d is None:
            return mt+" "+yt
        if y is not None and m is None and d is not None:
            return "mon?"+" "+dt+", "+yt
        if y is not None and m is None and d is None:
            return yt
        if y is None and m is not None and d is not None:
            return mt +" "+dt
        if y is None and m is not None and d is None:
            return mt
        if y is None and m is None and d is not None:
            return "Mon? "+dt+", Yr?"

        return "(undated)"


    # =============================================================================
    def FormatDateForSorting(self) -> str:               # FanzineDate
        y="0000"
        if self._Year is not None:
            y=YearName(self._Year)

        m="00"
        if self._Month is not None:
            m=format(self._Month, '02d')

        d="00"
        if self._Day is not None:
            d=format(self._Day, '02d')

        return y+"-"+m+"_"+d


    # =============================================================================
    # Parse a free-format string to find a date.  This tries to interpret the *whole* string as a date -- it doesn't find a date embeded in other text.
    @classmethod
    def Match(cls, s: str, strict: bool=False) -> FanzineDate:               # FanzineDate

        # Whitespace is not a date...
        dateText=s.strip()
        if len(dateText) == 0:
            return cls()

        # There are some dates which follow no useful pattern.  Check for them
        d=InterpretRandomDatestring(dateText)
        if d is not None:
            return d

        # The dateutil parser can handle a wide variety of date formats...but not all.
        # So the next step is to reduce some of the crud used by fanzines to an actual date.
        # We'll try a variety of patterns
        # Remove commas, which should never be significant
        dateText=dateText.replace(",", "").strip()

        # A 4-digit number all alone is a year
        m=re.compile("^(\d\d\d\d)$").match(dateText)  # Month + 2- or 4-digit year
        if m is not None and m.groups() is not None and len(m.groups()) == 1:
            y=ValidYear(m.groups()[0])
            if y is not None:
                return cls(Year=y)

        # Look for <month> <yy> or <yyyy> where month is a recognizable month name and the ys form a fannish year
        # Note that the mtext and ytext found here may be analyzed several different ways
        m=re.compile("^(.+)\s+(\d\d|\d\d\d\d)$").match(dateText)  # Month + 2- or 4-digit year
        if m is not None and m.groups() is not None and len(m.groups()) == 2:
            mtext=m.groups()[0]
            ytext=m.groups()[1]
            y=ValidYear(ytext)
            if y is not None and mtext is not None:
                if InterpretMonth(mtext) is not None:
                    md=InterpretMonthDay(mtext)
                    if md is not None:
                        return cls(Year=ytext, Month=md[0], Day=md[1])

            # If  a year was found but no valid month, try one of the weird month-day formats.
            if y is not None and mtext is not None:
                rslt=InterpretNamedDay(mtext)  # mtext was extracted by whichever pattern recognized the year and set y to non-None
                if rslt is not None:
                    return cls(Year=y, Month=rslt[0], Day=rslt[1], MonthDayText=mtext)

            # There are some words which are relative terms "late september", "Mid february" etc.
            # Give them a try.
            if y is not None and mtext is not None:
                # In this case the *last* token is assumed to be a month and all previous tokens to be the relative stuff
                tokens=mtext.replace("-", " ").replace(",", " ").split()
                if tokens is not None and len(tokens) > 0:
                    modifier=" ".join(tokens[:-1])
                    mtext=tokens[-1:][0]
                    m=MonthNameToInt(mtext)
                    d=InterpretRelativeWords(modifier)
                    if m is not None and d is not None:
                        return cls(Year=y, Month=m, Day=(d, modifier))

        # There are a few annoying entries of the form "Winter 1951-52"  They all *appear* to mean something like January 1952
        # We'll try to handle this case
        p=re.compile("^Winter\s+\d\d\d\d\s*-\s*(\d\d)$")
        m=p.match(dateText)
        if m is not None and len(m.groups()) == 1:
            return cls(Year=int(m.groups()[0]), Month=1, MonthText="Winter")  # Use the second part (the 4-digit year)

        # There there are the equally annoying entries Month-Month year (e.g., 'June - July 2001')
        # These will be taken to mean the first month
        # We'll look for the pattern <text> '-' <text> <year> with (maybe) spaces between the tokens
        p=re.compile("^(\w+)\s*-\s*(\w+)\s,?\s*(\d\d\d\d)$")
        m=p.match(dateText)
        if m is not None and len(m.groups()) == 3:
            month1=m.groups()[0]
            month2=m.groups()[1]
            year=m.groups()[2]
            m=InterpretMonth(month1)
            y=int(year)
            if m is not None:
                return cls(Year=y, Month=m, MonthText=month1+"-"+month2)

        # Next we'll look for yyyy-yy all alone
        p=re.compile("^\d\d\d\d\s*-\s*(\d\d)$")
        m=p.match(dateText)
        if m is not None and len(m.groups()) == 1:
            return cls(Year=int(m.groups()[0]), Month=1)    # Use the second part of the year, and given that this is yyyy-yy, it probably is a vaguely winterish date

        # Another form is the fannish "April 31, 1967" -- didn't want to miss that April mailing date!
        # We look for <month><number>,<year> with possible spaces between. Comma is optional.
        m=re.match(r"^(\w+)\s+(\d+),?\s+(\d\d|\d\d\d\d)$", dateText)  # Month + Day, + 2- or 4-digit year
        if m is not None and m.groups() is not None and len(m.groups()) == 3:
            mtext=m.groups()[0]
            dtext=m.groups()[1]
            ytext=m.groups()[2]
            y=int(ValidYear(ytext))
            m=InterpretMonth(mtext)
            d=InterpretDay(dtext)
            if y is not None and m is not None and d is not None:
                bd, bm, by=BoundDay(d, m, y)
                if bd != d or bm != m or by != y :
                    return cls(Year=by, Month=bm, Day=bd)

        # Try dateutil's parser on the string
        # If it works, we've got an answer. If not, we'll keep trying.
        # It is pretty aggressive, so only use it when strict is not set
        if not strict:
            with suppress(Exception):
                d=parser.parse(dateText, default=datetime.datetime(1, 1, 1))
                if d != datetime.datetime(1, 1, 1):
                    return cls(Year=d.year, Month=d.month, Day=d.day)

        # Nothing worked
        return cls()


#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
class FanzineSerial:

    def __init__(self, Vol=None, Num=None, NumSuffix=None, Whole=None, WSuffix=None) -> None:
        self.Vol=Vol
        self.Num=Num
        self.NumSuffix=NumSuffix  # For things like issue '17a'
        self.Whole=Whole
        self.WSuffix=WSuffix
        #self._UninterpretableText=None  # Ok, I give up.  Just hold the text as text.
        #self._TrailingGarbage=None  # The uninterpretable stuff following the interpretable spec held in this instance

    # Are the Num fields equal?
    # Both could be None; otherwise both must be equal
    def __NumEq__(self, other) -> bool:             # FanzineSerial
        return self._Num == other._Num and CaseInsensitiveCompare(self._NumSuffix, other._NumSuffix)

    def __VolEq__(self, other) -> bool:             # FanzineSerial
        return self._Vol == other._Vol

    def __WEq__(self, other) -> bool:             # FanzineSerial
        return self._Whole == other._Whole and CaseInsensitiveCompare(self._WSuffix, other._WSuffix)

    def __VNEq__(self, other) -> bool:             # FanzineSerial
        return self.__VolEq__(other) and self.__NumEq__(other)

    # Two issue designations are deemed to be equal if they are identical or if the VN matches while at least on of the Wholes in None or
    # is the Whole matches and at least one of the Vs and Ns is None.  (We would allow match of (W13, V3, N2) with (W13), etc.)
    def __eq__(self, other) -> bool:             # FanzineSerial
        # if the Whole numbers match, the two are the same. (Even if the Vol/Num differ.)
        # TODO: Should we check WSuffix?
        if self._Whole is not None and self._Whole == other._Whole:
            return True
        # If the wholes match and the Vol/Num match, they are the same
        if self.__WEq__(other) and self.__VNEq__(other):
            return True
        # if one of the Wholes is None and the Vol/Num match, the two are the same
        # TODO: Should we check NumSuffix?
        if (self._Whole is None or other._Whole is None) and self.__VNEq__(other):
            return True
        return False

    def __ne__(self, other) -> bool:             # FanzineSerial
        return not self.__eq__(other)

    # -----------------------------
    # Define < operator for sorting
    def __lt__(self, other: FanzineSerial) -> bool:             # FanzineSerial
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


    def Copy(self, other: FanzineSerial) -> None:             # FanzineSerial
        self._Vol=other._Vol
        self._Num=other._Num
        self._NumSuffix=other._NumSuffix
        self._Whole=other._Whole
        self._WSuffix=other._WSuffix
        #self._UninterpretableText=other._UninterpretableText
        #self._TrailingGarbage=other._TrailingGarbage

    # .....................
    @property
    def Vol(self) -> Optional[int]:             # FanzineSerial
        return self._Vol

    @Vol.setter
    def Vol(self, val: Union[None, int, str]) -> None:             # FanzineSerial
        if val is None:
            self._Vol=None
        elif isinstance(val, str):
            self._Vol=ToNumeric(val)
        else:
            self._Vol=val

    # .....................
    @property
    def Num(self) -> Optional[int]:             # FanzineSerial
        return self._Num

    @Num.setter
    def Num(self, val: Union[None, int, str]) -> None:             # FanzineSerial
        if val is None:
            self._Num=None
        elif isinstance(val, str):
            self._Num=ToNumeric(val)
        else:
            self._Num=val

    # .....................
    @property
    def NumSuffix(self) -> Optional[str]:             # FanzineSerial
        return self._NumSuffix

    @NumSuffix.setter
    def NumSuffix(self, val: Optional[str]) -> None:             # FanzineSerial
        self._NumSuffix=val

    # .....................
    @property
    def Whole(self) -> Optional[int]:             # FanzineSerial
        return self._Whole

    @Whole.setter
    def Whole(self, val: Union[None, int, str]) -> None:             # FanzineSerial
        if val is None:
            self._Whole=None
        elif isinstance(val, str):
            self._Whole=ToNumeric(val)
        else:
            self._Whole=val


    # .....................
    @property
    def WSuffix(self) -> Optional[str]:             # FanzineSerial
        return self._WSuffix

    @WSuffix.setter
    def WSuffix(self, val: Optional[str]) -> None:             # FanzineSerial
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
    #@property
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


    # .....................
    # Does this instance have anything defined for the serial number?
    def IsEmpty(self) -> bool:             # FanzineSerial
        return not reduce(lambda a, b: a or b, [self._NumSuffix, self._Num, self._Whole, self._WSuffix, self._Vol])

        # .....................
    def SetWhole(self, num: int, suffix: str) -> FanzineSerial:             # FanzineSerial
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
    def DebugStr(self) -> str:             # FanzineSerial
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

    def __str__(self) -> str:             # FanzineSerial
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
    def DecodeIssueDesignation(self, s: str) -> Tuple[ Optional[int], Optional[int] ]:             # FanzineSerial
        with suppress(Exception):
            return None, int(s)

        # Ok, it's not a simple number.  Drop leading and trailing spaces and see if it of the form #nn
        s=s.strip().lower()
        if len(s) == 0:
            return None, None
        if s[0] == "#":
            s=s[1:]
            if len(s) == 0:
                return None, None
            with suppress(Exception):
                return None, int(s)

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
        with suppress(Exception):
            return int(spl[0]), int(spl[1])

        return None, None


    # =============================================================================
    # Format the Vol/Num/Whole information
    def FormatSerialForSorting(self) -> str:             # FanzineSerial
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
    #  leading=True means that we don't try to match the entire input, but just a greedy chunk at the beginning.
    #  strict=True means that we will not match potentially ambiguous or ill-formed strings

    # We accept:
    #       ...Vnn[,][ ]#nnn[ ]
    #       ...nnn nnn/nnn      a number followed by a fraction
    #       ...nnn/nnn[  ]      vol/num
    #       ...rrr/nnn          vol (in Roman numerals)/num
    #       ...nn.mm
    #       ...nn[ ]
    def Match(self, s: str, scan: bool=False, strict: bool=False) -> bool:             # FanzineSerial
        self.Vol=None
        self.Num=None
        self.NumSuffix=None
        self.Whole=None
        self.WSuffix=None

        s=s.strip()     # Remove leading and trailing whitespace

        # First look for a Vol+Num designation: Vnnn #mmm
        pat=r"^V(\d+)\s*#(\d+)(\w?)"
        # # Leading junk
        # Vnnn + optional whitespace
        # #nnn + optional single alphabetic character suffix
        m=re.match(pat, s)
        if m is not None and len(m.groups()) in [2, 3]:
            self.Vol=int(m.groups()[0])
            self.Num=int(m.groups()[1])
            if len(m.groups()) == 3:
                self.NumSuffix=m.groups()[2]
            return True

        p=re.compile("V[oO][lL]\s*(\d+)\s*#(\d+)(\w?)$")
        # # Leading stuff
        #  Vol (or VOL) + optional space + nnn + optional comma + optional space
        # + #nnn + optional single alphabetic character suffix
        m=p.match(s)
        if m is not None and len(m.groups()) in [2, 3]:
            self.Vol=int(m.groups()[0])
            self.Num=int(m.groups()[1])
            if len(m.groups()) == 3:
                self.NumSuffix=m.groups()[2]
            return True

        # Now look for nnn nnn/nnn (fractions!)
        p=re.compile("^(\d+)\s+(\d+)/(\d+)$")  # nnn + mandatory whitespace + nnn + slash + nnn * optional whitespace
        m=p.match(s)
        if m is not None and len(m.groups()) == 3:
            self.Whole=int(m.groups()[0])+int(m.groups()[1])/int(m.groups()[2])
            return True

        # Now look for nnn/nnn (which is understood as vol/num
        p=re.compile("^(\d+)/(\d+)$")  # Leading stuff + nnn + slash + nnn * optional whitespace
        m=p.match(s)
        if m is not None and len(m.groups()) == 2:
            self.Vol=int(m.groups()[0])
            self.Num=int(m.groups()[1])
            return True

        # Now look for xxx/nnn, where xxx is in Roman numerals
        p=re.compile("^([IVXLC]+)/(\d+)$")  # Leading whitespace + roman numeral characters + slash + nnn + whitespace
        m=p.match(s)
        if m is not None and len(m.groups()) == 2:
            self.Vol=InterpretRoman(m.groups()[0])  #TODO: the regex detects more than just Roman numerals.  We need to bail out of this branch if that happens and not return
            self.Num=int(m.groups()[1])
            return True

        # Next look for nnn-nnn (which is a range of issue numbers; only the start is returned)
        p=re.compile("^(\d+)-(\d+)$")  # Leading stuff + nnn + dash + nnn
        m=p.match(s)
        if m is not None and len(m.groups()) == 2:
            self.Whole=int(m.groups()[0])
            return True

        # Next look for #nnn
        p=re.compile("^#(\d+)$")  # Leading stuff + nnn
        m=p.match(s)
        if m is not None and len(m.groups()) == 1:
            self.Whole=int(m.groups()[0])
            return True

        # Now look for a trailing decimal number
        p=re.compile("^.*?(\d+\.\d+)$")  # Leading characters + single non-digit + nnn + dot + nnn + whitespace
        # the ? makes * a non-greedy quantifier
        m=p.match(s)
        if m is not None and len(m.groups()) == 1:
            self.Vol=None
            self.Num=float(m.groups()[0])
            return True

        if not strict:
            # Now look for a single trailing number
            p=re.compile("^.*?([0-9]+)([a-zA-Z]?)\s*$")  # Leading stuff + nnn + optional single alphabetic character suffix + whitespace
            m=p.match(s)
            if m is not None and len(m.groups()) in [1, 2]:
                self.Whole=int(m.groups()[0])
                if len(m.groups()) == 2:
                    self.WSuffix=m.groups()[1].strip()
                return True

            # Now look for trailing Roman numerals
            p=re.compile("^.*?\s+([IVXLC]+)\s*$")  # Leading stuff + mandatory whitespace + roman numeral characters + optional trailing whitespace
            m=p.match(s)
            if m is not None and len(m.groups()) == 1:
                self.Num=InterpretRoman(m.groups()[0])
                return True

        # No good, return failure
        return False

#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
class FanzineIssueSpec:

    def __init__(self, Vol=None, Num=None, NumSuffix=None, Whole=None, WSuffix=None, Year=None, Month=None, MonthText=None, Day=None, DayText=None) -> None:
        self._FS=FanzineSerial(Vol=Vol, Num=Num, NumSuffix=NumSuffix, Whole=Whole, WSuffix=WSuffix)
        self._FD=FanzineDate(Year=Year, Month=Month, MonthText=MonthText, Day=Day, DayText=DayText)
        #self.UninterpretableText=None   # Ok, I give up.  Just hold the text as text.
        #self.TrailingGarbage=None       # The uninterpretable stuff following the interpretable spec held in this instance

    # Two issue designations are deemed to be equal if they are identical or if the VN matches while at least on of the Wholes in None or
    # is the Whole matches and at least one of the Vs and Ns is None.  (We would allow match of (W13, V3, N2) with (W13), etc.)
    def __IssueEQ__(self, other: FanzineIssueSpec) -> bool:         # FanzineIssueSpec
        return self._FS == other._FS

    def __DateEq__(self, other: FanzineIssueSpec) -> bool:         # FanzineIssueSpec
        return self._FD == other._FD

    # Class equality check.
    def __eq__(self, other: FanzineIssueSpec) -> bool:         # FanzineIssueSpec
        return self._FS == other._FS and self._FD == other._FD

    def __ne__(self, other: FanzineIssueSpec):         # FanzineIssueSpec
        return not self.__eq__(other)

    #-----------------------------
    # Define < operator for sorting
    def __lt__(self, other: FanzineIssueSpec) -> bool:         # FanzineIssueSpec
        if other is None:
            return False
        if self._FD is not None and other._FD is not None:
            return self._FD < other._FD
        if self._FS is not None and other._FS is not None:
            return self._FS < other._FS
        return False

    def Copy(self, other: FanzineIssueSpec) -> None:         # FanzineIssueSpec
        self._FD=other._FD
        self._FS=other._FS
        #self._UninterpretableText=other._UninterpretableText
        #self._TrailingGarbage=other._TrailingGarbage

    # .....................
    @property
    def FD(self) -> Optional[FanzineDate]:         # FanzineIssueSpec
        return self._FD

    @FD.setter
    def FD(self, val: FanzineDate) -> None:         # FanzineIssueSpec
        self._FD=val

    # .....................
    @property
    def FS(self) ->Optional[FanzineSerial]:         # FanzineIssueSpec
        return self._FS

    @FS.setter
    def FS(self, val: FanzineDate) -> None:         # FanzineIssueSpec
        self._FS=val

    # .....................
    @property
    def Vol(self) -> Optional[int]:         # FanzineIssueSpec
        return self._FS.Vol

    @Vol.setter
    def Vol(self, val: Optional[int, str]) -> None:         # FanzineIssueSpec
        if val is not None and isinstance(val, str) and len(val) == 0:
            self._FS.Vol=None
        else:
            self._FS.Vol=ToNumeric(val)

    # .....................
    @property
    def Num(self) -> Optional[int]:         # FanzineIssueSpec
        return self._FS.Num

    @Num.setter
    def Num(self, val: Optional[int, str]) -> None:         # FanzineIssueSpec
        if val is not None and isinstance(val, str) and len(val) == 0:
            self._FS.Num=None
        else:
            self._FS.Num=ToNumeric(val)

    # .....................
    @property
    def NumSuffix(self) -> Optional[str]:         # FanzineIssueSpec
        return self._FS.NumSuffix

    @NumSuffix.setter
    def NumSuffix(self, val: Optional[str]) -> None:         # FanzineIssueSpec
        if val is not None and isinstance(val, str) and len(val) == 0:
            self._FS.NumSuffix=None
        else:
            self._FS.NumSuffix=val

    #.....................
    @property
    def Whole(self) -> Optional[int]:         # FanzineIssueSpec
        return self._FS.Whole

    @Whole.setter
    def Whole(self, val: Optional[int, str]) -> None:         # FanzineIssueSpec
        if val is not None and isinstance(val, str) and len(val) == 0:
            self._FS.Whole=None
        else:
            self._FS.Whole=ToNumeric(val)


    # .....................
    @property
    def WSuffix(self) -> Optional[str]:         # FanzineIssueSpec
        return self._FS.WSuffix

    @WSuffix.setter
    def WSuffix(self, val: Optional[str]) -> None:         # FanzineIssueSpec
        if val is not None and isinstance(val, str) and len(val) == 0:
            self._FS.WSuffix=None
        else:
            self._FS.WSuffix=val

    #.....................
    @property
    def Year(self) -> Optional[int]:         # FanzineIssueSpec
        return self._FD.Year

    @Year.setter
    def Year(self, val: Optional[int, str]) -> None:         # FanzineIssueSpec
        self._FS.Year=val

    #.....................
    # This is a non-settable property -- it is always derived from the numeric Year
    @property
    def YearText(self) -> Optional[str]:         # FanzineIssueSpec
        return self._FD.YearText

    #.....................
    @property
    def Month(self) ->Optional[int]:         # FanzineIssueSpec
        return self._FD.Month

    @Month.setter
    def Month(self, val: Optional[int, str]) -> None:         # FanzineIssueSpec
        self._FD.Month=val

    #.....................
    @property
    def MonthText(self) -> Optional[str]:         # FanzineIssueSpec
        return self._FD.MonthText


    #.....................
    @property
    def Day(self) -> Optional[int]:         # FanzineIssueSpec
        return self._FD.Day

    @Day.setter
    def Day(self, val: Optional[int]) -> None:         # FanzineIssueSpec
        self._FD.Day=val

    # .....................
    @property
    def DayText(self) -> Optional[str]:         # FanzineIssueSpec
        return self._FD.DayText
    # There is no setter; Setting should be done when creating the instance or through the Day setter

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
    def DateStr(self) -> str:         # FanzineIssueSpec
        return str(self._FD)

    @property
    def SerialStr(self) -> str:         # FanzineIssueSpec
        return str(self._FS)

    # .....................
    # Return a datetime.date object
    def Date(self) -> datetime.date:         # FanzineIssueSpec
        return self._FD.Date

    # .....................
    def SetWhole(self, num: int, suffix: str) -> None:         # FanzineIssueSpec
        self._FS.SetWhole(num, suffix)

    #.......................
    # Convert the FanzineIssueSpec into a debugging form
    def DebugStr(self) -> str:         # FanzineIssueSpec
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
    def IsEmpty(self) -> bool:         # FanzineIssueSpec
        return self._FD.IsEmpty() and self._FS.IsEmpty()


    #.......................
    # Convert the FanzineIssueSpec into a pretty string for display or printing
    def __str__(self) -> str:         # FanzineIssueSpec
        # if self.UninterpretableText is not None:
        #     return self.UninterpretableText.strip()

        tg=""
        # if self.TrailingGarbage is not None:
        #     tg=" "+self.TrailingGarbage

        if not self._FD.IsEmpty():
            tg+=" "+str(self._FD)

        if not self._FS.IsEmpty():
            tg+="  "+str(self._FS)

        return tg.strip()

    # =====================================================================================
#    def DecodeIssueDesignation(self, s: str) -> None:         # FanzineIssueSpec
#        self._FS.DecodeIssueDesignation(s)


    # =====================================================================================
    # Take the input string and turn it into a FIS
    # The input could be a single date or it could be a single serial ID or it could be a range (e.g., 12-17)
    def Match(self, s: str, strict: bool = False):        # FanzineIssueSpec
        fis=FanzineIssueSpec()

        # A number standing by itself is messy, since it's easy to confuse with a date
        # In the FanzineIssueSpec world, we will always treat it as a Serial, so look for that first
        m=re.match("^(\d+)$", s)
        if m is not None and len(m.groups()) == 1:
            fs=FanzineSerial()
            fs.Whole=m.groups()[0]
            fis.FS=fs
            self.Copy(fis)  # We do the copy so any pre-existing date information gets overwritten
            return True

        # First try a date, and interpret it strictly no matter what the parameter says -- we can try non-strict later
        fd=FanzineDate().Match(s, strict=True)
        if not fd.IsEmpty():
            fis.FD=fd
            self.Copy(fis)
            return True

        # OK, it's probably not a date.  So try it as a serial ID
        fs=FanzineSerial()
        rslt=fs.Match(s, strict=strict)
        if rslt:
            fis.FS=fs
            self.Copy(fis)
            return True

        # That didn't work, either.  Try a non-strict date followed by a non-strict serial
        # OK, it's probably not a date.  So try it as a serial ID
        fs=FanzineSerial()
        rslt=fs.Match(s)
        if rslt:
            fis.FS=fs
            self.Copy(fis)
            return True

        # No good.  Failed.
        return False


    # =====================================================================================
    # Look for a FIS in the input string.  Return a tuple of (success, <unmatched text>)
    def Scan(self, s: str, strict: bool=False) -> Tuple[bool, str]:        # FanzineIssueSpec
        raise Exception


    #=============================================================================
    def FormatDateForSorting(self) -> str:         # FanzineIssueSpec
        return self._FD.FormatDateForSorting()

    #=============================================================================
    # Format the Vol/Num/Whole information
    def FormatSerialForSorting(self) -> str:         # FanzineIssueSpec
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
    def __init__(self, List: Optional[List[FanzineIssueSpec]]=None) -> None:      # FanzineIssueSpecList
        self.List=List  # Use setter

    def AppendIS(self, fanzineIssueSpec: Union[None, FanzineIssueSpec, FanzineIssueSpecList]) -> None:      # FanzineIssueSpecList
        if fanzineIssueSpec is None:
            return
        self.Extend(fanzineIssueSpec)
        return

    def Append(self, lst: Union[List[FanzineIssueSpec], FanzineIssueSpec]) -> FanzineIssueSpecList:      # FanzineIssueSpecList
        return self.Extend(lst)

    def Extend(self, val: Union[List[FanzineIssueSpec], FanzineIssueSpec]) -> FanzineIssueSpecList:      # FanzineIssueSpecList
        if self._List is None:
            self._List=[]
        if isinstance(val, list):
            raise Exception("FanzineIssueSpecList.Extend was called with a plain old list[]")
        elif isinstance(val, FanzineIssueSpecList):
            self._List.extend(val)
        else:
            self._List.append(val)
        return self


    def DebugStr(self) -> str:      # FanzineIssueSpecList
        s=""
        if self._List is not None:
            for i in self._List:
                if len(s) > 0:
                    s=s+",  "
                if i is not None:
                    s=s+i.DebugStr()
                else:
                    s=s+"Missing ISList"
        if len(s) == 0:
            s="Empty ISlist"
        return s


    def __str__(self) -> str:   # Format the ISL for pretty      # FanzineIssueSpecList
        s=""
        for i in self._List:
            if i is not None:
                if len(s) > 0:
                    s=s+", "
                s=s+str(i)
        return s

    def __len__(self) -> int:
        return len(self._List)

    @property
    def List(self) -> FanzineIssueSpecList:      # FanzineIssueSpecList
        return self._List

    @List.setter
    def List(self, val: Optional[FanzineIssueSpec, FanzineIssueSpecList]) -> None:      # FanzineIssueSpecList
        if val is None:
            self._List=[]
            return
        if isinstance(val, FanzineIssueSpec):
            self._List=[val]
            return
        if isinstance(val, FanzineIssueSpecList):
            self._List=val.List
            return
        Log("****FanzineIssueSpecList.List setter() had strange input")

    @List.getter
    def List(self) -> FanzineIssueSpecList:      # FanzineIssueSpecList
        return self._List

    def __getitem__(self, key: int) -> FanzineIssueSpec:      # FanzineIssueSpecList
        return self._List[key]

    def __setitem__(self, key: int, value: FanzineIssueSpec) -> FanzineIssueSpecList:      # FanzineIssueSpecList
        self.List[key]=value
        return self


    # =====================================================================================
    # Pull a Serial off of the end of a string
    def GetTrailingSerial(self, s: str) -> Tuple[Optional[FanzineIssueSpecList], str]:       # FanzineIssueSpecList
        # Try to greedily interpret the trailing text as a FanzineIssueSpec.
        # We do this by interpreting more and more tokens starting from the end until we have something that is no longer recognizable as a FanzineIssueSpec
        # The just-previous set of tokens constitutes the full IssueSpec, and the remaining leading tokens are the series name.
        tokens=s.split()  # Split into tokens on spaces
        leadingText=s
        fisl=None
        for index in range(len(tokens)-1, -1, -1):  # Ugly, but I need index to be the indexes of the tokens
            trailingText=" ".join(tokens[index:])
            leadingText=" ".join(tokens[:index])
            print("     index="+str(index)+"   leading='"+leadingText+"'    trailing='"+trailingText+"'")
            trialfisl=FanzineIssueSpecList()
            if not trialfisl.Match(trailingText, strict=True):  # Failed.  We've gone one too far. Quit trying and use what we found on the previous iteration
                print("     ...backtracking. FISL="+trialfisl.DebugStr())
                leadingText=" ".join(tokens[0:index+1])
                break
            fisl=trialfisl
        # At this point, leadingText is the fanzine's series name and fisl is a list of FanzineSerials found for it
        return fisl, leadingText

    #------------------------------------------------------------------------------------
    # Take the input string and turn it into a FISL
    def Match(self, s: str, strict: bool=False) -> bool:      # FanzineIssueSpecList
        fisl=FanzineIssueSpecList()

        # A FISL is comma-delimited with one exception: some dates include a comma (e.g., January 1, 2001")
        tokens=[t.strip() for t in s.split(",")]
        while len(tokens) > 0:
            # If there are at least two tokens left, re-join them and see if the result is an FIS of the form <Month> [day], yyyy
            if len(tokens) > 1:
                # Token 0 must contain a month name as its first token and may not start with a digit
                if not tokens[0][0].isdigit() and MonthNameToInt(tokens[0].split()[0]) is not None:
                    # Token 1 must be a 4-digit year
                    if re.match("^\d{4}$", tokens[1]) is not None:
                        # The put them together and try to interpret as a date
                        trial=tokens[0]+", "+tokens[1]
                        fis=FanzineIssueSpec()
                        if fis.Match(trial, strict=True):
                            fisl.Append(fis)
                            del tokens[0:1]
                            continue
            # The two together didn't work, so just try one
            # The first thing to look for is a range denoting multiple issues.  This will necessarily contain a hyphen.
            if "-" in tokens[0]:
                subtokens=tokens[0].split("-")
                # For now, at least, we can only handle the case of two subtokens, each of which are integers and the first is the smaller
                if len(subtokens) != 2:
                    Log("FanzineIssueSpecList:Match: Other than two subtokens found in '"+s+"'")
                    return False
                if not IsInt(subtokens[0]) or not IsInt(subtokens[1]) or int(subtokens[0]) >= int(subtokens[1]):
                    Log("FanzineIssueSpecList:Match: bad range values in '"+s+"'")
                    return False
                for i in range(int(subtokens[0]), int(subtokens[1])+1):
                    fisl.Append(FanzineIssueSpec(Whole=i))
                del tokens[0]
                continue

            # Now just look for a single issue
            fis=FanzineIssueSpec()
            if fis.Match(tokens[0], strict=strict):
                fisl.Append(fis)
                del tokens[0]
                continue

            # Nothing worked, so we won't have an FISL
            return False

        # Apparently we consumed the whole input.  Update self and return True
        self.List=fisl
        return True


    #------------------------------------------------------------------------------------
    # Look for a FISL in the input string.  Return a tuple of (success, <unmatched text>)
    def Scan(self, s: str, strict: bool=False) -> Tuple[bool, str]:      # FanzineIssueSpecList
        raise Exception

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
    with suppress(Exception):
        return namedDayConverstionTable[dayString.lower()]

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

    with suppress(Exception):
        return conversionTable[daystring.replace(",", " ").replace("-", " ").lower()]

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
# Take a string which suppoedly designates a year and return either a valid fannish year or None
def ValidYear(ytext: str) -> Optional[str]:
    if ytext is None:
        return None
    y=YearAs4Digits(ytext)
    if 1860 < y < 2100:     # numbers outside this range of years can't be a fannish date
        return str(y)
    return None


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
        with suppress(Exception):
            if '-' in yearText:
                years=yearText.split("-")
                if len(years) == 2:
                    y1=YearAs4Digits(int(years[0]))
                    y2=YearAs4Digits(int(years[1]))
                    return max(y1, y2)

    Log("   ***Year conversion failed: '"+yearText+"'", isError=True)
    return None


# =================================================================================
# Turn day into an int
def InterpretDay(dayData: Optional[int, str]) -> Optional[int]:

    if dayData is None:
        return None
    if isinstance(dayData, int):  # If it's already an int, not to worry
        return dayData
    if len(dayData.strip()) == 0:  # If it's blank, return None
        return None

    # Convert to int
    dayData=RemoveHTMLDebris(dayData)
    if len(dayData) == 0:
        return None
    try:
        day=int(dayData)
    except:
        d=InterpretNamedDay(dayData)
        if d is None:
            Log("   ***Day conversion failed: '"+dayData+"'", isError=True)
            day=None
        else:
            day=d[0]
    return day


# =================================================================================
# Validate data according to its type
def ValidateData(val: str, type: str) -> int:
    if val is None or len(val) == 0:
        return True

    type=CanonicizeColumnHeaders(type)
    if type == "Date":
        return InterpretRandomDatestring(val) is not None
    if type == "Day":
        return InterpretDay(val)
    if type == "Month":
        return InterpretMonth(val) is not None
    if type == "Number":
        return IsInt(val)
    if type == "Pages":
        return IsInt(val)
    if type == "Volume":
        return IsInt(val)
    if type == "Vol+Num":
        return False        # TODO: Fix this
    if type == "Whole":
        return IsInt(val)
    if type == "Year":
        return len(val) == 4 and  IsInt(val) and Int(val) > 1860 and Int(val) < 2050      # These numbers are chosen to represent the range of potentially valid fannish years.

    # For all other types we return True as we can't judge validity.
    return True


# =================================================================================
def MonthLength(m: int) -> int:
    if m == 2:   # This messes up leap years. De minimus
        return 28
    if m in [4, 6, 9, 11]:
        return 30
    if m in [1, 3, 5, 7, 8, 10, 12]:
        return 31

# =================================================================================
# Make sure day is within month
# We take a month and day and return a month and day
def BoundDay(d: Optional[int], m: Optional[int], y: Optional[int]) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    if d is None:
        return None, None, None
    if m is None:    # Should never happen!
        return None, None, None

    if d < -10 or d > 60:   # Dates this far off the month are more probably typos than deliberate.
        return None, None, None

    # Deal with the normal case
    if d >= 1 and d <= MonthLength(m):
        return d, m, y

    # Deal with negative days
    if d < 1:
        while d < 1:
            m=m-1
            if m < 1:
                m=12
                y=y-1
            d=d+MonthLength(m)
        return d, m, y

    # The day is past the end of the month.  Move it to the next month.
    while d > MonthLength(m):
        d=d-MonthLength(m)
        m=m+1
        if m > 12:
            m=1
            y=y+1

    return d, m, y


# =================================================================================
# Deal with things of the form "June 20," and "20 June" and just "June"
# Return a tuple of (month, day)
# (Day defaults to 1 if no day was supplied.)
def InterpretMonthDay(s: str) -> Optional[Tuple[int, Optional[int]]]:
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
            return m, None

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

    with suppress(Exception):
        return monthConversionTable[text]

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
    numsuffix=None
    maybeWholeInt=None
    wsuffix=None

    if wholeText is not None:
        wholeInt=InterpretNumber(wholeText)

    if volNumText is not None:
        ser=FanzineSerial()
        ser.Match(volNumText)
        if ser.Vol is not None and ser.Num is not None:  # Otherwise, we don't actually have a volume+number
            volInt=ser.Vol
            numInt=ser.Num
            numsuffix=ser.NumSuffix

    if volText is not None:
        volInt=InterpretNumber(volText)

    # If there's no vol, anything under "Num", etc., must actually be a whole number
    if volText is None:
        with suppress(Exception):
            maybeWholeText=numText
            maybeWholeInt=int(maybeWholeText)
            numText=None

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
        maybeWholeInt=None  #TODO: What is this?

    # Next, look at the title -- titles often have a serial designation at their end.

    if titleText is not None:
        # Possible formats:
        #   n   -- a whole number
        #   n.m -- a decimal number
        #   Vn  -- a volume number, but where's the issue?
        #   Vn[,] #m  -- a volume and number-within-volume
        #   Vn.m -- ditto
        ser=FanzineSerial()
        ser.Match(titleText if type(titleText) is not list else titleText[0])

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

            numsuffix=ser.NumSuffix
            wsuffix=ser.WSuffix

    return FanzineSerial(Vol=volInt, Num=numInt, NumSuffix=numsuffix, Whole=wholeInt, WSuffix=wsuffix)