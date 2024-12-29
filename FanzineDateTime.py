from __future__ import annotations
from datetime import datetime
from dateutil import parser
import re
from contextlib import suppress
import math

from Log import Log, LogError
from HelpersPackage import ToNumeric, IsNumeric, IsInt, Int
from HelpersPackage import RemoveHTMLDebris
from HelpersPackage import CanonicizeColumnHeaders


class FanzineDate:
    def __init__(self,
                 Year: int|str|None=None,
                 Month: int|str|tuple[int, str]|None=None,
                 MonthText: str|None=None,
                 Day: int|str|tuple[int, str]|None=None,
                 DayText: str|None=None,
                 MonthDayText: str|None =None,
                 DateTime: datetime|None = None) -> None:

        if DateTime is not None:
            self.DateTime=DateTime
            return

        self.Year=Year

        self._Month=None
        self._MonthText=None
        if not isinstance(Month, tuple) and MonthText is not None:
            Month=(Month, MonthText)
        self.Month=Month
        if Month is None and MonthText is not None:
            self.Month=InterpretMonth(MonthText)        # If only Monthtext is defined, use it to calculate Month

        self._Day=None
        self._DayText=None
        if isinstance(Day, tuple):
            self.Day=Day
        elif Day is not None and DayText is not None:
            self.Day=(Day, DayText)
        elif Day is not None and DayText is None:
            self.Day=Day
        elif Day is None and DayText is not None:        # If only DayText is defined, use it to calculate Day
            self.Day=InterpretDay(DayText)

        self._MonthDayText=MonthDayText                 # Overrides display of both month and day, but has no other effect
        self._LongDates=False


    def __hash__(self) -> int:
        return hash(self.Year)+hash(self.Month)+hash(self.MonthText)+hash(self.Day)+hash(self.DayText)+hash(self.MonthDayText)


    # -----------------------------
    def __eq__(self, other: Self) -> bool:
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

    # -----------------------------
    def __ne__(self, other: Self) -> bool:
        return not self.__eq__(other)

    def __sub__(self, other):
        y1=self.Year if self.Year is not None else 1
        m1=self.Month if self.Month is not None else 1
        d1=self.Day if self.Day is not None else 1
        y2=other.Year if other.Year is not None else 1
        m2=other.Month if other.Month is not None else 1
        d2=other.Day if other.Day is not None else 1
        try:
            return (datetime(y1, m1, d1) - datetime(y2, m2, d2)).days
        except:
            Log("*** We have a problem subtracting two dates: "+str(self)+ " - "+str(other))
            return 0

    # -----------------------------
    # Define < operator for sorting
    def __lt__(self, other: Self) -> bool:
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

    # -----------------------------
    def Copy(self, other: Self) -> None:
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
    def LongDates(self):
        self._LongDates=True        # Set _LongDates to True.  The next use of __str__() will set it back to False
        return self                 # This was str(FD) will yield short dates and str(FD.LongDates) will yield long dates

    #......................
    @property
    def DateTime(self):
        return self.DateTime
    @DateTime.setter
    def DateTime(self, val: datetime):
        #assert type(val) is datetime
        self.Year=val.year
        self.Month=val.month
        self.Day=val.day

    # .....................
    @property
    def Year(self) -> int:
        return self._Year
    @Year.setter
    def Year(self, val: int|str) -> None:
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
    def Month(self, val: int|str|tuple[int, str]) -> None:
        if isinstance(val, str):
            self._Month=InterpretMonth(val)     # If you supply only the MonthText, the Month number is computed
            self._MonthText=val if (val is not None and len(val) > 0) else None
        elif isinstance(val, tuple):    # Use the Tuple to set both Month and MonthText
            self._Month=val[0]
            self._MonthText=val[1] if (val[1] is not None and len(val) > 0) else None
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
    def MonthText(self, mt: str):
        self._MonthText=mt

    # .....................
    @property
    def Day(self) -> int:
        return self._Day
    @Day.setter
    def Day(self, val: int|str|tuple[int, str]) -> None:
        if isinstance(val, str):    # If you supply only the DayText, the Day number is computed
            self._Day=ToNumeric(val) if (val is not None and len(val) > 0) else None
            self._DayText=val if (val is not None and len(val) > 0) else None
        elif isinstance(val, tuple):    # Use the Tuple to set both Day and DayText
            self._Day=val[0]
            self._DayText=val[1] if (val[1] is not None  and len(val) > 0) else None
        else:
            self._Day=val
            self._DayText=None  # If we set a numeric day, any day text gets blown away as no longer relevant

    # .....................
    @property
    def DayText(self) -> str|None:
        if self._DayText is not None:
            return self._DayText
        if self._Day is not None:
            return DayName(self._Day)
        return ""
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
    def Date(self) -> datetime.date|None:
        if self.IsEmpty():
            return None
        y=self._Year if self._Year is not None else 1
        m=self._Month if self._Month is not None else 1
        d=self._Day if self._Day is not None else 1
        return datetime(y, m, d).date

    # .......................
    # Convert the FanzineDate into a debugging form
    def __repr__(self) -> str:
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
    def IsEmpty(self) -> bool:
        if self._DayText is not None and len(self._DayText) > 0:
            return False
        if self._Day is not None:
            return False
        if self._Month is not None:
            return False
        if self._Year is not None:
            return False
        if self._MonthText is not None and len(self._MonthText) > 0:
            return False
        return True

    # .......................
    # Convert the FanzineIssueSpec into a pretty string for display or printing
    def __str__(self) -> str:
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
    def FormatDateForSorting(self) -> str:
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
    def FormatDate(self, fmt: str) -> str:
        if self.Date is None:
            return ""
        return self.Date.strftime(fmt)


    # =============================================================================
    # Parse a free-format string to find a date.  This tries to interpret the *whole* string as a date -- it doesn't find a date embeded in other text.
    # strict=true means that dubious forms will be rejected
    # complete=True means that *all* the input string must be part of the date
    @classmethod
    def Match(cls, s: str, strict: bool=False, complete: bool=True) -> Self:

        self=cls()

        # Whitespace is not a date...
        dateText=s.strip()
        if len(dateText) == 0:
            return self

        # Turn any long dashes and double hyphens into single hyphens
        dateText=dateText.replace('—', '-')
        dateText=dateText.replace('--', '-')

        # There are some dates which follow no useful pattern.  Check for them
        d=InterpretRandomDatestring(dateText)
        if d is not None:
            return d

        # A 4-digit number all alone is a year
        m=re.match(r"^(\d\d\d\d)$", dateText)  # Month + 2- or 4-digit year
        if m is not None and m.groups() is not None and len(m.groups()) == 1:
            y=ValidFannishYear(m.groups()[0])
            if y != "0":
                self.Year=y
                return self

        # Look for mm/dd/yy and mm/dd/yyyy
        m=re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})$", dateText)
        if m is not None and m.groups() is not None and len(m.groups()) == 3:
            g1t=m.groups()[0]
            g2t=m.groups()[1]
            yt=m.groups()[2]
            y=int(ValidFannishYear(yt))
            if y is not None:
                # The US date format has the first group as the month and the second as the day.  See if this works.
                m=int(g1t)
                d=int(g2t)
                if ValidateDay(d, m, y):
                    self.Year=y
                    self.Month=m
                    self.Day=d
                    return self

                # Maybe European date format?
                d=int(g1t)
                m=int(g2t)
                if ValidateDay(d, m, y):
                    self.Year=y
                    self.Month=m
                    self.Day=d
                    return self

        # Look for <month> <yy> or <yyyy> where month is a recognizable month name and the <y>s form a fannish year
        # Note that the mtext and ytext found here may be analyzed several different ways
        m=re.match(r"^([\s\w\-',]+).?\s+(\d\d|\d\d\d\d)$", dateText)  # Month +[,] + 2- or 4-digit year
        if m is not None and m.groups() is not None and len(m.groups()) == 2:
            mtext=m.groups()[0].replace(","," ").replace("  ", " ")     # Turn a comma-space combination into a single space
            ytext=m.groups()[1]
            y=ValidFannishYear(ytext)
            if y is not None and mtext is not None:
                if InterpretMonth(mtext) is not None:
                    md=InterpretMonthDay(mtext)
                    if md is not None:
                        self.Year=ytext
                        self.Month=md[0]
                        self.Day=md[1]
                        return self

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
                        self.Year=y
                        self.Month=m
                        self.Day=(d, modifier)
                        return self

        # Annoyingly, the standard date parser doesn't like "." designating an abbreviated month name.  Deal with mmm. dd, yyyy
        m=re.match(r"^([\s\w\-',]+).?\s+(\d+),?\s+(\d\d|\d\d\d\d)$", dateText)  # Month +[,] + 2- or 4-digit year
        if m is not None and m.groups() is not None and len(m.groups()) == 3:
            mtext=m.groups()[0].replace(","," ").replace("  ", " ")     # Turn a comma-space combination into a single space
            dtext=m.groups()[1]
            ytext=m.groups()[2]
            y=ValidFannishYear(ytext)
            if y is not None and mtext is not None:
                m=InterpretMonth(mtext)
                if m is not None:
                    self.Year=ytext
                    self.Month=m
                    self.Day=Int(dtext)
                    return self

        # Look for <dd> <month> [,] <yyyy> where month is a recognizable month name and the <y>s form a fannish year
        # Note that the mtext and ytext found here may be analyzed several different ways
        m=re.match(r"^(\d{1,2})\s+([\s\w\-',]+).?\s+(\d\d|\d\d\d\d)$", dateText)  # Month +[,] + 2- or 4-digit year
        if m is not None and m.groups() is not None and len(m.groups()) == 3:
            dtext=m.groups()[0]
            mtext=m.groups()[1].replace(",", " ").replace("  ", " ")  # Turn a comma-space combination into a single space
            ytext=m.groups()[2]
            y=ValidFannishYear(ytext)
            if y is not None and mtext is not None:
                m=InterpretMonth(mtext)
                if m is not None:
                    self.Year=ytext
                    self.Month=m
                    self.Day=Int(dtext)
                    return self

        # There are some weird day/month formats (E.g., "St. Urho's Day 2013")
        # Look for a pattern of: <strange day/month> <year>
        m=re.match(r"^(.+?)[,\s]+(\d\d|\d\d\d\d)$", dateText)  # random text + space + 2- or 4-digit year
        if m is not None and m.groups() is not None and len(m.groups()) == 2:
            mtext=m.groups()[0].replace(","," ").replace("  ", " ")     # Turn a comma-space combination into a single space
            ytext=m.groups()[1]
            y=ValidFannishYear(ytext)
            if y is not None and mtext is not None:
                rslt=InterpretNamedDay(mtext)  # mtext was extracted by whichever pattern recognized the year and set y to non-None
                if rslt is not None:
                    self.Year=y
                    self.Month=rslt[0]
                    self.Day=rslt[1]
                    self.MonDayText=mtext
                    return self

        # There are a few annoying entries of the form "Winter 1951-52"  They all *appear* to mean something like January 1952
        # We'll try to handle this case
        m=re.match(r"^Winter[,\s]+\d\d\d\d\s*-\s*(\d\d)$", dateText)
        if m is not None and len(m.groups()) == 1:
            return cls(Year=int(m.groups()[0]), Month=1, MonthText="Winter")  # Use the second part (the 4-digit year)

        # There are the equally annoying entries Month-Month year (e.g., 'June - July 2001') and Month/Month year.
        # These will be taken to mean the first month
        # We'll look for the pattern <text> '-' <text> <year> with (maybe) spaces between the tokens
        m=re.match(r"^(\w+)\s*[-/]\s*(\w+)\s,?\s*(\d\d\d\d)$", dateText)
        if m is not None and len(m.groups()) == 3:
            month1=m.groups()[0]
            month2=m.groups()[1]
            year=m.groups()[2]
            m=InterpretMonth(month1)
            y=int(year)
            if m is not None:
                self.Year=y
                self.Month=m
                self.MonthText=month1+"-"+month2
                return self

        # Next we'll look for yyyy-yy all alone
        m=re.match(r"^\d\d\d\d\s*-\s*(\d\d)$", dateText)
        if m is not None and len(m.groups()) == 1:
            self.Year=int(m.groups()[0])
            self.Month=1
            return self
            # Use the second part of the year, and given that this is yyyy-yy, it probably is a vaguely winterish date

        # Another form is the fannish "April 31, 1967" -- didn't want to miss that April mailing date!
        # We look for <month><number>,<year> with possible spaces between. Comma is optional.
        m=re.match(r"^(\w+)\s+(\d+),?\s+(\d\d|\d\d\d\d)$", dateText)  # Month + Day, + 2- or 4-digit year
        if m is not None and m.groups() is not None and len(m.groups()) == 3:
            mtext=m.groups()[0]
            dtext=m.groups()[1]
            ytext=m.groups()[2]
            y=int(ValidFannishYear(ytext))
            m=InterpretMonth(mtext)
            d=InterpretDay(dtext)
            if y is not None and m is not None and d is not None:
                bd, bm, by=BoundDay(d, m, y)
                self.Year=by
                self.Month=bm
                self.Day=bd
                return self

        # Try dateutil's parser on the string
        # If it works, we've got an answer. If not, we'll keep trying.
        # It is pretty aggressive, so only use it when strict is not set
        if not strict and not complete:
            with suppress(Exception):
                d=parser.parse(dateText, default=datetime(1, 1, 1))
                if d != datetime(1, 1, 1):
                    self.Year=d.year
                    self.Month=d.month
                    self.Day=d.day
                    return self

        # Nothing worked
        return self


#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
class FanzineDateRange:
    def __init__(self):
        self._startdate: FanzineDate|None=None
        self._enddate: FanzineDate|None=None
        self._cancelled: bool=False
        self._useMarkupForCancelled: bool=False


    def Copy(self, val: "FanzineDateRange"):
        self._startdate=FanzineDate()
        self._startdate.Copy(val._startdate)
        self._enddate=FanzineDate()
        self._enddate.Copy(val._enddate)
        self._cancelled=val._cancelled
        self._useMarkupForCancelled=val._useMarkupForCancelled

        return self

    # -----------------------------
    def __hash__(self):
        return hash(self._startdate)+hash(self._enddate)+hash(self._cancelled)
    #TODO:  What about _useMarkupForCancelled?

    # -----------------------------
    def __eq__(self, other: "FanzineDateRange") -> bool:
            return self._startdate == other._startdate and self._enddate == other._enddate

    # -----------------------------
    def __lt__(self, other: "FanzineDateRange") -> bool:
        if self._startdate < other._startdate:
            return True
        if self._startdate == other._startdate:
            return self._enddate < other._enddate
        return False

    # -----------------------------
    def __str__(self) -> str:
        d1=self._startdate
        d2=self._enddate
        if d1 is None and d2 is None:
            return ""
        if d1 is None and d2 is not None:
            s=str(d2)
        elif d1 is not None and d2 is None:
            s=str(d1)
        elif d1.Year == d2.Year:
            if d1.Month == d2.Month:
                if d1.Month is None:
                    s=str(d1.Year)
                elif d1.Day == d2.Day:
                    if d1.Day is None:
                        s=MonthName(d1.Month)+" "+str(d1.Year)
                    else:
                        s=MonthName(d1.Month)+" "+str(d1.Day)+", "+str(d1.Year)
                else:
                    s=MonthName(d1.Month)+" "+str(d1.Day)+"-"+str(d2.Day)+", "+str(d1.Year)
            else:
                s=MonthName(d1.Month)+" "+str(d1.Day)+"-"+MonthName(d2.Month)+" "+str(d2.Day)+", "+str(d1.Year)
        else:
            s=str(d1)+"-"+str(d2)

        if self._cancelled:
            if self._useMarkupForCancelled:
                s=f"<s>{s}</s>"
            else:
                s+=" (cancelled)"

        return s

    @property
    def StartDate(self) -> FanzineDate:
        return self._startdate

    @property
    def EndDate(self) -> FanzineDate:
        return self._enddate

    # .....................
    @property
    def Cancelled(self) -> bool:
        return self._cancelled

    @Cancelled.setter
    def Cancelled(self, val: bool) -> None:
        self._cancelled=val

    #...................
    def Match(self, s: str, strict: bool=False, complete: bool=True) -> "FanzineDateRange":
        if s is None:
            return self

        # Whitespace is not a date...
        dateText=s.strip()
        if len(dateText) == 0:
            return self

        # Strip bracketing <s></s>
        m=re.match(r"\s*<s>(.*)</s>\s*$", s)
        if m:
            self._cancelled=True
            self._useMarkupForCancelled=True
            s=m.groups()[0]

        # If we have a single "-", then the format is probably of the form:
        #   #1: <month+day>-<month+day> year  or
        #   #2: <month> <day>-<day> <year>
        #   #3: <day>-<day> <month>[,] <year>
        #   #4: <month+day> <year1> - <month+day> <year2>
        s=s.replace("–", "-")   # Convert en-dash to hyphen
        s=s.replace("—", "-")  # Convert em-dash to hyphen
        s=s.replace("--", "-")  # Likewise double-hyphens
        s=s.replace("  ", " ").replace("  ", " ")  # Collapse strings of spaces
        s=s.replace(" -", "-").replace("- ", "-")  # Remove spaces around "-"
        if s.count("-") == 1:   # There's got to be exactly one hyphen for it to be an interpretable date range

            # Try format #1: <monthday>-<monthday> year  or
            # s2 should contain a full date, including year
            s1, s2=s.split("-")
            d2=FanzineDate().Match(s2)
            if not d2.IsEmpty() and not d2.Day is None and not d2.Month is None:
                # Add s2's year to the end of s1
                s1+=" "+str(d2.Year)
                d1=FanzineDate().Match(s1)
                if not d1.IsEmpty() and not d1.Day is None and not d1.Month is None:
                    self._startdate=d1
                    self._enddate=d2
                    return self

            # Try format #2: <month> <day>-<day>[,] <year>
            # Split on blanks, then recombine the middle parts
            slist=[s for s in re.split(r'[ \-,]+',s) if len(s) > 0]  # Split on spans of space, hyphen and comma; ignore empty splits
            if len(slist) == 4:
                m=slist[0]
                if not IsInt(m):    # m must be a text month -- it can't be a number
                    y=slist[3]
                    d1=FanzineDate().Match(m+" "+slist[1]+", "+y)
                    d2=FanzineDate().Match(m+" "+slist[2]+", "+y)
                    if not d1.IsEmpty() and not d2.IsEmpty():
                        self._startdate=d1
                        self._enddate=d2
                        return self

            # Try 3: <day>-<day> <month>[,] <year>
            slist=s.split()
            if len(slist) > 2:
                if "-" in slist[0]:
                    s1, s2=slist[0].split("-")
                    d1=FanzineDate().Match(s1+" "+slist[1]+" "+slist[2])
                    if not d1.IsEmpty():
                        d2=FanzineDate().Match(s2+" "+slist[1]+" "+slist[2])
                        if not d2.IsEmpty():
                            self._startdate=d1
                            self._enddate=d2
                            return self

            # Well, then what about #4?
            slist=s.split("-")
            d1=FanzineDate().Match(slist[0])
            if not d1.IsEmpty():
                d2=FanzineDate().Match(slist[1])
                if not d2.IsEmpty():
                    self._startdate=d1
                    self._enddate=d2
                    return self

        # Try just an ordinary single date
        d=FanzineDate().Match(s)
        if not d.IsEmpty():
            self._startdate=d
            self._enddate=d
            return self

        # Oh, well.
        return self

    #...................
    def IsEmpty(self) -> bool:
        return self._startdate is None or self._startdate.IsEmpty() or self._enddate is None or self._enddate.IsEmpty()

    # ...................
    # Return the duration of the range in days
    def Duration(self) -> int:
        if self._enddate is None or self._startdate is None:
            return 0
        return self._enddate-self._startdate

    def IsOdd(self) -> bool:
        if self._enddate is None or self._startdate is None:
            return True
        if self.Duration() > 5:
            return True
        if self._startdate.IsEmpty() or self._enddate.IsEmpty():
            return True
        return False

    @property
    def DisplayDaterangeBare(self) -> str:
        saved=self._cancelled
        self._cancelled=False
        s=self.__str__()
        self._cancelled=saved
        return s

#=================================================================================
# Deal with things of the form "June 20," and "20 June" and just "June"
# Return a tuple of (month, day)
# (Day defaults to 1 if no day was supplied.)
def InterpretMonthDay(s: str) -> tuple[int, int|None]|None:
    s=s.strip() # Get rid of leading and trailing blanks as they can't possibly be of interest
    s=s.removesuffix(",")    # Get rid of trailing comma

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
def InterpretMonth(monthData: str|int|None) -> int|None:

    if monthData is None:
        return None
    if isinstance(monthData, int):
        return monthData
    if len(monthData.strip()) == 0:  # If it's blank, return 0
        return None

    monthData=RemoveHTMLDebris(monthData)
    if len(monthData) == 0:
        return None

    # If it ends in a "." it may be abbreviated. Remove trailing "."
    monthData=monthData.removesuffix(".")

    return MonthNameToInt(monthData)

# =================================================================================
# Turn day into an int
def InterpretDay(dayData: int|str|None)-> int|None:

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
            LogError("   ***Day conversion failed: '"+dayData+"'")
            day=None
        else:
            day=d[0]
    return day


# =================================================================================
# Validate data according to its type
def ValidateData(val: str, valtype: str) -> int:
    if val is None or len(val) == 0:
        return True

    valtype=CanonicizeColumnHeaders(valtype)
    if valtype == "Date":
        return InterpretRandomDatestring(val) is not None
    if valtype == "Day":
        return InterpretDay(val)
    if valtype == "Month":
        return InterpretMonth(val) is not None
    if valtype == "Number":
        return IsInt(val)
    if valtype == "Pages":
        return IsInt(val)
    if valtype == "Volume":
        return IsInt(val)
    if valtype == "Vol+Num":
        return False        # TODO: Fix this
    if valtype == "Whole":
        return IsInt(val)
    if valtype == "Year":
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
def BoundDay(d: int|None, m: int|None, y: int|None) -> tuple[int|None, int|None, int|None]:
    if d is None:
        return None, None, None
    if m is None:    # Should never happen!
        return None, None, None

    if d < -10 or d > 60:   # Dates this far off the month are more probably typos than deliberate.
        return None, None, None

    # Deal with the normal case
    if 1 <= d <= MonthLength(m):
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


# ====================================================================================
# Convert a text month to integer
def MonthNameToInt(text: str) -> int|None:
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
    m=re.match("^([a-z]+)[-/]([a-z]+)$", text)
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
def InterpretRandomDatestring(text: str) -> FanzineDate|None:
    text=text.lower().replace(",", "")
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
    if text == "october 2013 halloween":
        return FanzineDate(Year=2013, Month=10, DayText="Halloween", Day=31)
    if text == "october (halloween) 2015":
        return FanzineDate(Year=2015, Month=10, DayText="Halloween", Day=31)
    if text == "november (december) 2015":
        return FanzineDate(Year=2015, Month=12, DayText="November (December)", Day=1)
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

# =================================================================================
# Convert 2-digit years to four digit years
# We accept 2-digit years from 1933 to 2032
def YearAs4Digits(year: int|str|None)-> int|None:
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
# Take a string which supposedly designates a year and return either a valid fannish year or None
def ValidFannishYear(ytext: str) -> str:
    if ytext is None:
        return "0"  # error
    y=YearAs4Digits(ytext)
    if 1860 < y < 2100:     # numbers outside this range of years can't be a fannish date
        return str(y)
    return "0"  # error


# =================================================================================
# Take a day and month and (optionally) year and check for consistency
def ValidateDay(d: int, m: int, year: int=None) -> bool:
    monthlength=MonthLength(m)
    # Handle leap years
    if year is not None and year%4 == 0 and year % 400 != 0:
        if m == 2:
            monthlength=29
    if d is None or monthlength is None:
        return False
    return 0 < d <= monthlength


# =================================================================================
# Turn year into an int
def InterpretYear(yearText: int|str|None)-> int|str|None:

    if yearText is None:
        return None
    if isinstance(yearText, int):  # If it's already an int, not to worry
        return yearText
    if len(yearText.strip()) == 0:  # If it's blank, return 0
        return None

    yearText=RemoveHTMLDebris(yearText)  # We treat <br> and </br> as whitespace, also
    if len(yearText) == 0:
        return None

    # Drop up to two trailing question mark(s)
    yearText=yearText.removesuffix("?").removesuffix("?")

    # Convert to int
    try:
        return YearAs4Digits(int(yearText))
    except:
        # OK, that failed. Could it be because it's something like '1953-54'?
        with suppress(Exception):
            if '-' in yearText or '–' in yearText:
                years=yearText.split("-")
                if len(years) == 1:
                    years=years[0].split("–")   # Try the longer dash
                if len(years) == 2:
                    y1=YearAs4Digits(int(years[0]))
                    y2=YearAs4Digits(int(years[1]))
                    return max(y1, y2)

    LogError("   ***Year conversion failed: '"+yearText+"'")
    return None

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
def YearName(year: int|str|None)-> str:
    if year is None or year == 0:
        return ""
    return str(YearAs4Digits(year))


# ====================================================================================
#  Handle dates like "Thanksgiving"
# Returns a month/day tuple which will often be exactly correct and rarely off by enough to matter
# Note that we don't (currently) attempt to handle moveable feasts by taking the year in account
def InterpretNamedDay(dayString: str) -> tuple[int, int]|None:
    namedDayConversionTable={
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
        "Late february or early march": (3, None),
        "ides of march": (3, 15),
        "st urho's day": (3, 16),
        "st. urho's day": (3, 16),
        "saint urho's day": (3, 16),
        "vernal equinox": (3, 20),
        "spring equinox": (3, 20),
        "april fool's day": (4, 1),
        "good friday": (4, 8),
        "solar eclipse": (4,8),     # 2024 only...
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
        "calgary stampede parade": (7, 10),
        "system administrator appreciation day": (7, 25),
        "apres le deluge": (8, 1),  # Opuntia, 2013 Calgary floods
        "august 14 to 16": (8, 15),
        "international whale shark day": (8, 30),
        "labor day": (9, 3),
        "labour day": (9, 3),
        "september 15 to 18": (9, 17),
        "september 17 to 20": (9, 19),
        "autumn equinox": (9, 20),
        "fall equinox": (9, 20),
        "(canadian) thanksgiving": (10, 15),
        "halloween": (10, 31),
        "october (halloween)": (10, 31),
        "remembrance day": (11, 11),
        "rememberance day": (11, 11),
        "thanksgiving": (11, 24),
        ''"around the end"'': (12, None),
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
        ''"over year end"'': (12, 31)
    }
    with suppress(Exception):
        return namedDayConversionTable[dayString.lower().replace(",", "")]

    return None


# ====================================================================================
# Deal with situations like "late December"
# We replace the vague relative term by a non-vague (albeit unreasonably precise) number
def InterpretRelativeWords(daystring: str) -> int|None:
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
