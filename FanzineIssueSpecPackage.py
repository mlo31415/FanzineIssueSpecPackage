# This package of classes provides support for naming and listing fanzines.
# It consists of five classes
#   FanzineSerial           -- contains a single serial number (V4#3, #22, #7A, VII, etc)
#   FanzineDate             -- contains a date (June, 1949; 2005; 2/22/79; etc)
#   FanzineIssueSpec        -- contains a FanzineDate and a FanzineSerial providing a complete sequence designation for an issue
#                              it contains no other information about the issue such as name or series
#   FanzineIssueSpecList    -- contains a list of FanzineIssueSpecs all relevant to a single fanzine
#                              It differs  from a FanzineSeriesList in that it contains a list of FanzineIssueSpecs and not a list of FanzineIssueInfos
#   FanzineIssueInfo        -- contains information for a single issue (title, editor, sequence, etc). Includes a FanzineIssueSpec
#   FanzineSeriesList       -- contains information for a fanzine series (Locus, VOID, File 770, Axe, etc). Includes a list of FanzineIssueInfos

# A FanzineIssueSpec contains the information for one fanzine issue's specification, e.g.:
#  V1#2, #3, #2a, Dec 1967, etc.
# It can be a volume+number or a whole number or a date. (It can be more than one of these, also, and all are retained.)

# The top level is a FanzineIssueSpecList which holds many FanzineIssueSpecs
# A FanzineIssueSpec holds the serial number and date for a single issue
#     It also holds a FanzineSerial and a FanzineDate which hold, respectively, the issue designation and the issue date
#     (This would also be the right place to put other issue-specific information such as editor, pagecount, etc.)
#     (It probably should be merged with the FanzineIssueData class of 1943FanzineList)
from __future__ import annotations
from typing import Union, Optional

import math
import re
from contextlib import suppress
import datetime
from dateutil import parser
import json

from Locale import Locale

from Log import Log, LogError
from HelpersPackage import ToNumeric, IsNumeric, IsInt, Int
from HelpersPackage import Pluralize
from HelpersPackage import RemoveHTMLDebris
from HelpersPackage import InterpretNumber, InterpretRoman, InterpretInteger
from HelpersPackage import CaseInsensitiveCompare
from HelpersPackage import CanonicizeColumnHeaders
from HelpersPackage import ParmDict

class FanzineCounts:
    def __init__(self, Titlecount: int=0, Issuecount: int=0, Pagecount: int=0, Pdfcount: int=0, Pdfpagecount: int=0, Title: str=None, Titlelist: set[str]=None):

        if Titlelist is None:
            self.Titlelist: set=set()       # A set to hold title names.  This is needed to count titles when fanzines are not ordered in title order
        else:
            self.Titlelist=Titlelist
        if Title:
            self.Titlelist.add(Title)
        self.Titlecount: int=Titlecount  # Count of distinct titles.
        self.Issuecount: int=Issuecount  # Count of issues in all the titles
        self.Pagecount: int=Pagecount   # Cumulative page count for all the issues
        self.Pdfcount: int=Pdfcount     # Count of issues which are PDFs
        self.Pdfpagecount: int=Pdfpagecount
        if self.Issuecount == 0 and self.Pagecount > 0:   # If it is initialized with a pagecount only, add an issue count of 1
            self.Issuecount=1

    # .....................
    def __str__(self) -> str:  # FanzineCounts
        s=""
        t=self.Titlecount
        if t == 0 and len(self.Titlelist) > 0:
            t=len(self.Titlelist)
        i=self.Issuecount
        p=self.Pagecount
        if t > 0:
            s+=Pluralize(t, "title", Spacechar="&nbsp;")+", "
        if i > 0:
            s+=Pluralize(i, "issue", Spacechar="&nbsp;")+", "
            s+=Pluralize(p, "page", Spacechar="&nbsp;")
        return s

    # .....................
    def __add__(self, b: [FanzineCounts | FanzineIssueInfo | int | str]) -> FanzineCounts:  # FanzineCounts
        # Note that titlecount, pdfcount and pdfpagecount need to be incremented (or not) independently
        if type(b) is FanzineCounts:
            return FanzineCounts(Issuecount=self.Issuecount+b.Issuecount, Pagecount=self.Pagecount+b.Pagecount, Titlecount=self.Titlecount, Pdfcount=self.Pdfcount, Pdfpagecount=self.Pdfpagecount, Titlelist=self.Titlelist)
        elif type(b) is FanzineIssueInfo:
            return FanzineCounts(Issuecount=self.Issuecount+1, Pagecount=self.Pagecount+b.Pagecount, Titlecount=self.Titlecount, Pdfcount=self.Pdfcount, Pdfpagecount=self.Pdfpagecount, Titlelist=self.Titlelist)
        elif type(b) is int:
            # The int is taken to be a pagecount, and the issue count is automatically incremented
            return FanzineCounts(Issuecount=self.Issuecount+1, Pagecount=self.Pagecount+b, Titlecount=self.Titlecount, Pdfcount=self.Pdfcount, Pdfpagecount=self.Pdfpagecount, Titlelist=self.Titlelist)
        elif type(b) is str:
            return FanzineCounts(Issuecount=self.Issuecount, Pagecount=self.Pagecount, Titlecount=self.Titlecount, Pdfcount=self.Pdfcount, Pdfpagecount=self.Pdfpagecount, Titlelist=self.Titlelist)

        assert False

    #......................
    # Needed for += for mutable objects
    def __iadd__(self, b: [FanzineCounts | FanzineIssueInfo | int | str]) -> FanzineCounts:  # FanzineCounts
        # Note that titlecount, pdfcount and pdfpagecount need to be incremented (or not) independently
        if type(b) is FanzineCounts:
            self.Issuecount+=b.Issuecount
            self.Pagecount+=b.Pagecount
            return self
        elif type(b) is FanzineIssueInfo:
            self.Issuecount+=1
            self.Pagecount+=b.Pagecount
            return self
        elif type(b) is int:
            # The int is taken to be a pagecount, and the issue count is automatically incremented
            self.Issuecount+=1
            self.Pagecount+=b
            return self
        elif type(b) is str:
            self.Titlelist.add(b)
            return self

        assert False

    # -------------------------------------------------------------------------
    # Compute a counts annotation from a 2-tuple element -- used in calls to WriteTable
    def Annotate(self, special: int=0) -> str:
        s=self.__str__()
        if s and special != 1:
            s="("+s+")"
        return s


############################################################################################
# A class holding information about a fanzine series
# Note that for onesies or some types we sometimes create an artificial  fanzine series to go with a single issues
class FanzineSeriesInfo:

    def __init__(self, SeriesName: str = "", DisplayName: str = "", DirURL: str = "", Issuecount: int=0,
                 Pagecount: int = 0, Editor: str = "", Country: str = "", AlphabetizeIndividually: bool=False, Keywords: ParmDict=None) -> None:
        _SeriesName: str=""  # Name of the fanzine series of which this is an issue
        _DisplayName: str=""  # Name to use for this issue. Includes issue serial and or date
        _DirURL: str=""  # URL of series directory
        _Counts: FanzineCounts  # Page and Issue count for all the issues fanac has for this series
        _Editor: str=""  # The editor for this series (if there was one for essentially all issues)
        _Country: str="" # The country for this issue (gotten from the series's country
        _AlphabetizeIndividually: bool=False
        _Keywords: ParmDict=ParmDict()  # A list of keywords

        # Use the properties to set the values for all of the instance variables. We do this so that any special setter processing is done with the init values.
        self.SeriesName=SeriesName
        self.DisplayName=DisplayName
        self.DirURL=DirURL
        self.Counts=FanzineCounts(Issuecount=Issuecount, Pagecount=Pagecount)
        self.Editor=Editor
        self.Country=Country
        self.AlphabetizeIndividually=AlphabetizeIndividually
        if Keywords == None:
            Keywords=ParmDict()
        self._Keywords=Keywords
        pass

    # .....................
    def __str__(self) -> str:  # FanzineSeriesInfo
        out=""
        if self.DisplayName != "":
            return self.DisplayName
        elif self.SeriesName != "":
            out=self.SeriesName

        return out.strip()

    # .....................
    def __repr__(self) -> str:  # FanzineSeriesInfo
        out=""
        if self.DisplayName != "":
            out="'"+self.DisplayName+"'"
        elif self.SeriesName != "":
            out=self.SeriesName

        if self.Editor != "":
            out+=f"  ed:{self.Editor}"
        if self.Issuecount > 0:
            out+=f"  {self.Issuecount} issues"
        if self.Pagecount > 0:
            out+=f"  {self.Pagecount} pp"
        if self.Country != "":
            out+=f"   ({self.Country})"
        return out.strip()

    # -----------------------------
    # Note that this ignores quite a lot in creating the hash value
    # Be careful!
    def __hash__(self):
        return hash(self._SeriesName)+hash(self._Editor)+hash(self._Country)

    # .....................
    # Note that page and issue count are not included in equality comparisons.
    # This allows for accumulation of those numbers while retaining series identity
    def __eq__(self, other: FanzineSeriesInfo) -> bool:  # FanzineSeriesInfo
        if other is None:
            return False

        if self._SeriesName != other._SeriesName:
            return False
        if self._Editor != other._Editor:
            return False
        if self._Country != other._Country:
            return False

        return True

    # .....................
    # When we add, we add to the counts
    def __add__(self, b: [FanzineSeriesInfo, FanzineIssueInfo, int]):  # FanzineSeriesInfo
        ret=FanzineSeriesInfo(SeriesName=self.SeriesName, Editor=self.Editor, DisplayName=self.DisplayName, Country=self.Country, DirURL=self.DirURL)
        #Log("FanzineSeriesInfo.add:  self.URL="+self.URL+"     b.URL="+b.URL)
        if type(b) is FanzineSeriesInfo:
            ret.Issuecount=self.Issuecount+b.Issuecount
            ret.Pagecount=self.Pagecount+b.Pagecount
        elif type(b) is FanzineIssueInfo:
            ret.Issuecount=self.Issuecount+1
            ret.Pagecount=self.Pagecount+b.Pagecount
        else:
            assert type(b) is int
            ret.Issuecount=self.Issuecount+1
            ret.Pagecount=self.Pagecount+b
        return ret

    # .....................
    # When we add, we add to the counts
    # Note that this is an in-paces add to aupport += for mutable objects
    def __iadd__(self, b: [FanzineSeriesInfo, FanzineIssueInfo, int]):  # FanzineSeriesInfo
        if type(b) is FanzineSeriesInfo:
            self.Issuecount+=b.Issuecount
            self.Pagecount+=b.Pagecount
        elif type(b) is FanzineIssueInfo:
            self.Issuecount+=1
            self.Pagecount+=b.Pagecount
        else:
            assert type(b) is int
            self.Issuecount+=1
            self.Pagecount+=b
        return self

    # .....................
    def Deepcopy(self) -> FanzineSeriesInfo:      #FanzineSeriesInfo
        new=FanzineSeriesInfo()
        new.SeriesName=self.SeriesName
        new.DisplayName=self.DisplayName
        new.DirURL=self.DirURL
        new.Pagecount=self.Pagecount
        new.Issuecount=self.Issuecount
        new.Editor=self.Editor
        new.Country=self.Country
        new.FanzineSeriesInfo=self.FanzineSeriesInfo
        return new

    # .....................
    def IsEmpty(self) -> bool:  # FanzineSeriesInfo
        if self.SeriesName != "":
            return False
        if self._DisplayName != "":
            return False
        if self.DirURL != "":
            return False
        if self.Editor != "":
            return False
        if str(self.Country) != "":
            return False
        
        return True

    # .....................
    @property
    def SeriesName(self) -> str:  # FanzineSeriesInfo
        return self._SeriesName
    @SeriesName.setter
    def SeriesName(self, val: str) -> None:  # FanzineSeriesInfo
        self._SeriesName=val.strip()

    # .....................
    @property
    def DisplayName(self) -> str:  # FanzineSeriesInfo
        if self._DisplayName != "":
            return self._DisplayName
        return self.SeriesName
    @DisplayName.setter
    def DisplayName(self, val: str) -> None:  # FanzineSeriesInfo
        self._DisplayName=val.strip()

    # .....................
    @property
    def DirURL(self) -> str:  # FanzineSeriesInfo
        return self._URL
    @DirURL.setter
    def DirURL(self, val: str) -> None:  # FanzineSeriesInfo
        self._URL=val

    # .....................
    @property
    def Counts(self) -> FanzineCounts:  # FanzineSeriesInfo
        return self._Counts
    @Counts.setter
    def Counts(self, val: FanzineCounts) -> None:  # FanzineSeriesInfo
        self._Counts=val

    # .....................
    @property
    def Pagecount(self) -> int:  # FanzineSeriesInfo
        return self._Counts.Pagecount
    @Pagecount.setter
    def Pagecount(self, val: int) -> None:  # FanzineSeriesInfo
        self._Counts.Pagecount=val
        
    # .....................
    @property
    def Issuecount(self) -> int:  # FanzineSeriesInfo
        return self._Counts.Issuecount
    @Issuecount.setter
    def Issuecount(self, val: int) -> None:  # FanzineSeriesInfo
        self._Counts.Issuecount=val

    # .....................
    # Needed for compatibility, but always zero
    @property
    def Titlecount(self) -> int:  # FanzineSeriesInfo
        return self._Counts.Titlecount

    # .....................
    @property
    def Country(self) -> str:  # FanzineSeriesInfo
        return self._Country
    @Country.setter
    def Country(self, val: str) -> None:  # FanzineSeriesInfo
        self._Country=val
        
    # .....................
    @property
    def Editor(self) -> str:  # FanzineSeriesInfo
        return self._Editor
    @Editor.setter
    def Editor(self, val: str) -> None:  # FanzineSeriesInfo
        self._Editor=val

    # .....................
    @property
    def AlphabetizeIndividually(self) -> bool:  # FanzineSeriesInfo
        return self._AlphabetizeIndividually
    @AlphabetizeIndividually.setter
    def AlphabetizeIndividually(self, val: bool) -> None:  # FanzineSeriesInfo
        if val is None:
            val=[]
        self._AlphabetizeIndividually=val

    # .....................
    @property
    def Keywords(self) -> ParmDict:     # FanzineSeriesInfo
        return self._Keywords
    # There is no setter
    def SetKeyword(self, kwd: str, val: str=""):
        self._Keywords[kwd]=val # If no value is suppled, we use ""


#---------------------------------------------------------------------------------------
class FanzineDate:
    def __init__(self,
                 Year: Union[int, str, None]=None,
                 Month: Union[int, str, tuple[int, str], None]=None,
                 MonthText: Optional[str]=None,
                 Day: Union[int, str, tuple[int, str], None]=None,
                 DayText: Optional[str]=None,
                 MonthDayText: Optional[str] =None,
                 DateTime: Optional[datetime] = None) -> None:

        if DateTime is not None:
            self.DateTime=DateTime
            return

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


    def __hash__(self) -> int:
        return hash(self.Year)+hash(self.Month)+hash(self.MonthText)+hash(self.Day)+hash(self.DayText)+hash(self.MonthDayText)

    def ToJson(self) -> str:
        d={"ver": 1,
           "_Year": self._Year,
           "_Month": self._Month,
           "_MonthText": self._MonthText,
           "_Day": self._Day,
           "_DayText": self._DayText,
           "_MonthDayText": self._MonthDayText,
           "_LongDates": self._LongDates}
        return json.dumps(d)

    def FromJson(self, val: str) -> FanzineDate:
        d=json.loads(val)
        self._Year=d["_Year"]
        self._Month=d["_Month"]
        self._MonthText=d["_MonthText"]
        self._Day=d["_Day"]
        self._DayText=d["_DayText"]
        self._MonthDayText=d["_MonthDayText"]
        self._LongDates=d["_LongDates"]
        return self

    # -----------------------------
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

    # -----------------------------
    def __ne__(self, other: FanzineDate) -> bool:               # FanzineDate
        return not self.__eq__(other)

    def __sub__(self, other):
        y1=self.Year if self.Year is not None else 1
        m1=self.Month if self.Month is not None else 1
        d1=self.Day if self.Day is not None else 1
        y2=other.Year if other.Year is not None else 1
        m2=other.Month if other.Month is not None else 1
        d2=other.Day if other.Day is not None else 1
        try:
            return (datetime.date(y1, m1, d1)-datetime.date(y2, m2, d2)).days
        except:
            Log("*** We have a problem subtracting two dates: "+str(self)+ " - "+str(other))
            return 0

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

    # -----------------------------
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
    def Month(self, val: Union[int, str, tuple[int, str]]) -> None:               # FanzineDate
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
    def MonthText(self) -> str:               # FanzineDate
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
    def Day(self) -> int:               # FanzineDate
        return self._Day
    @Day.setter
    def Day(self, val: Union[int, str, tuple[int, str]]) -> None:               # FanzineDate
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

    # .......................
    # Convert the FanzineDate into a debugging form
    def __repr__(self) -> str:               # FanzineDate
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
    def __str__(self) -> str:               # FanzineDate
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
    def FormatDate(self, fmt: str) -> str:               # FanzineDate
        if self.Date is None:
            return ""
        return self.Date.strftime(fmt)


    # =============================================================================
    # Parse a free-format string to find a date.  This tries to interpret the *whole* string as a date -- it doesn't find a date embeded in other text.
    # strict=true means that dubious forms will be rejected
    # complete=True means that *all* the input string much be part of the date
    @classmethod
    def Match(cls, s: str, strict: bool=False, complete: bool=True) -> FanzineDate:               # FanzineDate

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
        m=re.match("^(\d\d\d\d)$", dateText)  # Month + 2- or 4-digit year
        if m is not None and m.groups() is not None and len(m.groups()) == 1:
            y=ValidFannishYear(m.groups()[0])
            if y != "0":
                self.Year=y
                return self

        # Look for mm/dd/yy and mm/dd/yyyy
        m=re.match("^(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})$", dateText)
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
        m=re.match("^([\s\w\-',]+).?\s+(\d\d|\d\d\d\d)$", dateText)  # Month +[,] + 2- or 4-digit year
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
        m=re.match("^([\s\w\-',]+).?\s+(\d+),?\s+(\d\d|\d\d\d\d)$", dateText)  # Month +[,] + 2- or 4-digit year
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
        m=re.match("^([\d]{1,2})\s+([\s\w\-',]+).?\s+(\d\d|\d\d\d\d)$", dateText)  # Month +[,] + 2- or 4-digit year
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
        m=re.match("^(.+?)[,\s]+(\d\d|\d\d\d\d)$", dateText)  # random text + space + 2- or 4-digit year
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
        m=re.match("^Winter[,\s]+\d\d\d\d\s*-\s*(\d\d)$", dateText)
        if m is not None and len(m.groups()) == 1:
            return cls(Year=int(m.groups()[0]), Month=1, MonthText="Winter")  # Use the second part (the 4-digit year)

        # There are the equally annoying entries Month-Month year (e.g., 'June - July 2001') and Month/Month year.
        # These will be taken to mean the first month
        # We'll look for the pattern <text> '-' <text> <year> with (maybe) spaces between the tokens
        m=re.match("^(\w+)\s*[-/]\s*(\w+)\s,?\s*(\d\d\d\d)$", dateText)
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
        m=re.match("^\d\d\d\d\s*-\s*(\d\d)$", dateText)
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
                d=parser.parse(dateText, default=datetime.datetime(1, 1, 1))
                if d != datetime.datetime(1, 1, 1):
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
        self._startdate: Optional[FanzineDate]=None
        self._enddate: Optional[FanzineDate]=None
        self._cancelled: bool=False
        self._useMarkupForCancelled: bool=False

    def ToJson(self) -> str:
        d={"ver": 3,
            "_startdate": self._startdate.ToJson(),
            "_enddate": self._enddate.ToJson(),
            "_cancelled": self._cancelled,
            "__useMarkupForCancelled": self._useMarkupForCancelled}

        return json.dumps(d)

    def FromJson(self, val: str) -> FanzineDateRange:               # FanzineDateRange
        d=json.loads(val)
        ver=d["ver"]
        self._startdate=FanzineDate().FromJson(d["_startdate"])
        self._enddate=FanzineDate().FromJson(d["_enddate"])
        self._cancelled=False
        if ver > 1:
            self._cancelled=("true" == d["_cancelled"])
        if ver > 2:
            self._useMarkupForCancelled=("true" == d["_useMarkupForCancelled"])

        return self

    # -----------------------------
    def __hash__(self):
        return hash(self._startdate)+hash(self._enddate)+hash(self._cancelled)

    # -----------------------------
    def __eq__(self, other:FanzineDateRange) -> bool:               # FanzineDateRange
            return self._startdate == other._startdate and self._enddate == other._enddate

    # -----------------------------
    def __lt__(self, other:FanzineDateRange) -> bool:               # FanzineDateRange
        if self._startdate < other._startdate:
            return True
        if self._startdate == other._startdate:
            return self._enddate < other._enddate
        return False

    # -----------------------------
    def __str__(self) -> str:               # FanzineDateRange
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
    def Cancelled(self) -> bool:             # FanzineDateRange
        return self._cancelled
    @Cancelled.setter
    def Cancelled(self, val: bool) -> None:             # FanzineDateRange
        self._cancelled=val


    @property
    def DisplayDaterangeText(self) -> str:
        saved=self._useMarkupForCancelled
        self._useMarkupForCancelled=False
        s=self.__str__()
        self._useMarkupForCancelled=saved
        return s


    @property
    def DisplayDaterangeMarkup(self) -> str:
        saved=self._useMarkupForCancelled
        self._useMarkupForCancelled=True
        s=self.__str__()
        self._useMarkupForCancelled=saved
        return s


    @property
    def DisplayDaterangeBare(self) -> str:
        saved=self._cancelled
        self._cancelled=False
        s=self.__str__()
        self._cancelled=saved
        return s


    #...................
    def Match(self, s: str, strict: bool=False, complete: bool=True) -> FanzineDateRange:               # FanzineDateRange
        if s is None:
            return self

        # Whitespace is not a date...
        dateText=s.strip()
        if len(dateText) == 0:
            return self

        # Strip bracketing <s></s>
        m=re.match("\s*<s>(.*)<\/s>\s*$", s)
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
            slist=[s for s in re.split('[ \-,]+',s) if len(s) > 0]  # Split on spans of space, hyphen and comma; ignore empty splits
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
    def IsEmpty(self) -> bool:             # FanzineDateRange
        return self._startdate is None or self._startdate.IsEmpty() or self._enddate is None or self._enddate.IsEmpty()

    # ...................
    # Return the duration of the range in days
    def Duration(self) -> int:             # FanzineDateRange
        if self._enddate is None or self._startdate is None:
            return 0
        return self._enddate-self._startdate

    def IsOdd(self) -> bool:             # FanzineDateRange
        if self._enddate is None or self._startdate is None:
            return True
        if self.Duration() > 5:
            return True
        if self._startdate.IsEmpty() or self._enddate.IsEmpty():
            return True
        return False



#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

class FanzineSerial:

    def __init__(self, Vol: Union[None, int, str]=None, Num: Union[None, int, str, float]=None, NumSuffix: Optional[str]="", Whole: Union[None, int, str, float]=None, WSuffix: Optional[str]="") -> None:
        self._Vol=None
        self._Num=None
        self._Whole=None
        self._WSuffix=""
        self._NumSuffix=""

        self.Vol=Vol
        self.Num=Num
        self.NumSuffix=NumSuffix  # For things like issue '17a'
        self.Whole=Whole
        self.WSuffix=WSuffix
        pass

    # List class properties: [p for p in dir(FanzineSerial) if isinstance(getattr(FanzineSerial, p), property)]

    # import inspect
    # All functions: [name for (name, value) in inspect.getmembers(FanzineSerial)]
    # All functions and instance variables: [(name, value) for (name, value) in inspect.getmembers(self)]
    # Just properties [(name, value) for (name, value) in inspect.getmembers(self, lambda o: isinstance(o, property))]
    # source code: inspect.getsource(FanzineIssueSpecList.List.fget)
    # inspect.getsource(FanzineSerial.Whole.fget)

    # -----------------------------
    # Are the Num fields equal?
    # Both could be None; otherwise both must be equal
    def __NumEq__(self, other: FanzineSerial) -> bool:             # FanzineSerial
        return self._Num == other._Num and CaseInsensitiveCompare(self._NumSuffix, other._NumSuffix)

    # -----------------------------
    def __VolEq__(self, other: FanzineSerial) -> bool:             # FanzineSerial
        return self._Vol == other._Vol

    # -----------------------------
    def __WEq__(self, other: FanzineSerial) -> bool:             # FanzineSerial
        return self._Whole == other._Whole and CaseInsensitiveCompare(self._WSuffix, other._WSuffix)

    # -----------------------------
    def __VNEq__(self, other: FanzineSerial) -> bool:             # FanzineSerial
        return self.__VolEq__(other) and self.__NumEq__(other)

    # -----------------------------
    # Two issue designations are deemed to be equal if they are identical or if the VN matches while at least on of the Wholes in None or
    # is the Whole matches and at least one of the Vs and Ns is None.  (We would allow match of (W13, V3, N2) with (W13), etc.)
    def __eq__(self, other: FanzineSerial) -> bool:             # FanzineSerial
        # if the Whole numbers match, the two are the same. (Even if the Vol/Num differ.)
        if self._Whole is not None and self.__WEq__(other):
            return True
        # If the wholes match and the Vol/Num match, the two are the same
        if self.__WEq__(other) and self.__VNEq__(other):
            return True
        # if at least one of the Wholes is None and the Vol/Num match, the two are the same
        if (self._Whole is None or other._Whole is None) and self.__VNEq__(other):
            return True
        return False

    # -----------------------------
    def __ne__(self, other: FanzineSerial) -> bool:             # FanzineSerial
        return not self.__eq__(other)

    # -----------------------------
    # Define < operator for sorting
    # Is self less than other?
    def __lt__(self, other: FanzineSerial) -> bool:             # FanzineSerial
        if other is None:
            return False
        # If both have Wholes, use Whole for the comparison
        if self._Whole is not None and other._Whole is not None:
            if self._Whole < other._Whole:
                return True
            if self._Whole > other._Whole:
                return False

            # Can the suffixes provide a tie breaker?
            if self._WSuffix is not None or other._WSuffix is not None:
                # OK, the Wholes are equal.  Can the suffixs (e.g., #133 and #133A) be used to distinguish?  Suffixed Wholes are always larger.
                if other._WSuffix is None:
                    return False            # If other is None it can't be less that self, even if self, also, is None
                if self._WSuffix is None:
                    return True             # Other has a suffix and self doesn't, so self is less than other
                # Both have suffixes
                return self._WSuffix < other._WSuffix

        # Wholes were no help
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

    # -----------------------------
    def Copy(self, other: FanzineSerial) -> None:             # FanzineSerial
        self._Vol=other._Vol
        self._Num=other._Num
        self._NumSuffix=other._NumSuffix
        self._Whole=other._Whole
        self._WSuffix=other._WSuffix


    # -----------------------------
    def SetIntProperty(self, val: Union[None, int, str]) -> Optional[int]:
        if val is None:
            return None
        elif isinstance(val, str):
            return ToNumeric(val)
        return val

    # .....................
    @property
    def Vol(self) -> Optional[int]:             # FanzineSerial
        return self._Vol

    @Vol.setter
    def Vol(self, val: Union[None, int, str]) -> None:             # FanzineSerial
        self._Vol=self.SetIntProperty(val)

    # .....................
    @property
    def Num(self) -> Optional[int]:             # FanzineSerial
        return self._Num

    @Num.setter
    def Num(self, val: Union[None, int, str]) -> None:             # FanzineSerial
        self._Num=self.SetIntProperty(val)

    # .....................
    @property
    def NumSuffix(self) -> Optional[str]:             # FanzineSerial
        return self._NumSuffix

    @NumSuffix.setter
    def NumSuffix(self, val: Optional[str]) -> None:             # FanzineSerial
        if val is None:
            val=""
        self._NumSuffix=val

    # .....................
    @property
    def Whole(self) -> Optional[int]:                 # FanzineSerial
        return self._Whole

    @Whole.setter
    def Whole(self, val: Union[None, int, str]) -> None:             # FanzineSerial
        self._Whole=self.SetIntProperty(val)

    # .....................
    @property
    def WSuffix(self) -> Optional[str]:             # FanzineSerial
        return self._WSuffix

    @WSuffix.setter
    def WSuffix(self, val: Optional[str]) -> None:             # FanzineSerial
        if val is None:
            val=""
        self._WSuffix=val

    # .....................
    # Does this instance have anything defined for the serial number?
    def IsEmpty(self) -> bool:             # FanzineSerial
        if self._NumSuffix is not None and len(self._NumSuffix) > 0:
            return False
        if self._Num is not None:
            return False
        if self._Whole is not None:
            return False
        if self._Vol is not None:
            return False
        if self._WSuffix is not None and len(self._WSuffix) > 0:
            return False
        return True

    # .......................
    # Convert the FanzineIssueSpec into a debugging form
    def __repr__(self) -> str:             # FanzineSerial
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
    def DecodeIssueDesignation(self, s: str) -> tuple[ Optional[int], Optional[int] ]:             # FanzineSerial
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
    # complete=True means that we will only match the *complete* input (other than leading and trailing whitespace).

    # We accept:
    #       ...Vnn[,][ ]#nnn[ ]
    #       ...nnn nnn/nnn      a number followed by a fraction
    #       ...nnn/nnn[  ]      vol/num
    #       ...rrr/nnn          vol (in Roman numerals)/num
    #       ...nn.mm
    #       ...nn[ ]
    @classmethod
    def Match(cls, s: str, scan: bool=False, strict: bool=False, complete: bool=False):             # FanzineSerial
        s=s.strip()     # Remove leading and trailing whitespace

        # First look for a Vol+Num designation: Vnnn #mmm
        pat=r"^V(\d+)\s*#(\d+)(\w?)"
        # # Leading junk
        # Vnnn + optional whitespace
        # #nnn + optional single alphabetic character suffix
        m=re.match(pat, s)
        if m is not None and len(m.groups()) in [2, 3]:
            ns=None
            if len(m.groups()) == 3:
                ns=m.groups()[2]
            return cls(Vol=int(m.groups()[0]), Num=int(m.groups()[1]), NumSuffix=ns)

        #
        #  Vol (or VOL) + optional space + nnn + optional comma + optional space
        # + #nnn + optional single alphabetic character suffix
        m=re.match("V[oO][lL]\s*(\d+)\s*#(\d+)(\w?)$", s)
        if m is not None and len(m.groups()) in [2, 3]:
            ns=None
            if len(m.groups()) == 3:
                ns=m.groups()[2]
            return cls(Vol=int(m.groups()[0]), Num=int(m.groups()[1]), NumSuffix=ns)

        # Now look for nnn nnn/nnn (fractions!)
        # nnn + mandatory whitespace + nnn + slash + nnn * optional whitespace
        m=re.match("^(\d+)\s+(\d+)/(\d+)$", s)
        if m is not None and len(m.groups()) == 3:
            return cls(Whole=int(m.groups()[0])+int(m.groups()[1])/int(m.groups()[2]))

        # Now look for nnn/nnn (which is understood as vol/num
        # Leading stuff + nnn + slash + nnn * optional whitespace
        m=re.match("^(\d+)/(\d+)$", s)
        if m is not None and len(m.groups()) == 2:
            return cls(Vol=int(m.groups()[0]), Num=int(m.groups()[1]))

        # Now look for xxx/nnn, where xxx is in Roman numerals
        # Leading whitespace + roman numeral characters + slash + nnn + whitespace
        m=re.match("^([IVXLC]+)/(\d+)$", s)
        if m is not None and len(m.groups()) == 2:
            #TODO: the regex detects more than just Roman numerals.  We need to bail out of this branch if that happens and not return
            return cls(Vol=InterpretRoman(m.groups()[0]), Num=int(m.groups()[1]))

        # Next look for nnn-nnn (which is a range of issue numbers; only the start is returned)
        # Leading stuff + nnn + dash + nnn
        m=re.match("^(\d+)-(\d+)$", s)
        if m is not None and len(m.groups()) == 2:
            return cls(Whole=int(m.groups()[0]))

        # Next look for #nnn
        # Leading stuff + nnn
        m=re.match("^#(\d+)$", s)
        if m is not None and len(m.groups()) == 1:
            return cls(Whole=int(m.groups()[0]))

        # Now look for a trailing decimal number
        # Leading characters + single non-digit + nnn + dot + nnn + whitespace
        # the ? makes * a non-greedy quantifier
        m=re.match("^.*?(\d+\.\d+)$", s)
        if m is not None and len(m.groups()) == 1:
            return cls(Num=float(m.groups()[0]))

        if not strict and not complete:
            # Now look for a single trailing number
            # Leading stuff + nnn + optional single alphabetic character suffix + whitespace
            m=re.match("^.*?([0-9]+)([a-zA-Z]?)\s*$", s)
            if m is not None and len(m.groups()) in [1, 2]:
                ws=None
                if len(m.groups()) == 2:
                    ws=m.groups()[1].strip()
                return cls(Whole=int(m.groups()[0]), WSuffix=ws)

            # Now look for trailing Roman numerals
            # Leading stuff + mandatory whitespace + roman numeral characters + optional trailing whitespace
            m=re.match("^.*?\s+([IVXLC]+)\s*$", s)
            if m is not None and len(m.groups()) == 1:
                return cls(Num=InterpretRoman(m.groups()[0]))

        # No good, return failure
        return cls()


#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
class FanzineIssueSpec:

    def __init__(self, Vol: Union[None, int, str]=None,
                 Num: Union[None, int, str]=None,
                 NumSuffix: Optional[str]=None,
                 Whole: Union[None, int, str]=None,
                 WSuffix: Optional[str]=None,
                 Year: Optional[int]=None,
                 Month: Optional[int]=None,
                 MonthText: Optional[str]=None,
                 Day: Optional[int]=None,
                 DayText: Optional[str]=None,
                 FS: Optional[FanzineSerial]=None,
                 FD: Optional[FanzineDate]=None)\
            -> None:

        if FS is not None:
            self._FS=FS
        else:
            self._FS=FanzineSerial(Vol=Vol, Num=Num, NumSuffix=NumSuffix, Whole=Whole, WSuffix=WSuffix)

        if FD is not None:
            self._FD=FD
        else:
            self._FD=FanzineDate(Year=Year, Month=Month, MonthText=MonthText, Day=Day, DayText=DayText)

    # .......................
    # Convert the FanzineIssueSpec into a debugging form
    def __repr__(self) -> str:  # FanzineIssueSpec
        s="IS("+repr(self._FS)+" "+repr(self._FD)
        s=s+")"

        return s

    # .......................
    # Convert the FanzineIssueSpec into a pretty string for display or printing
    def __str__(self) -> str:  # FanzineIssueSpec
        tg=""
        if not self._FD.IsEmpty():
            tg+=" "+str(self._FD)

        if not self._FS.IsEmpty():
            tg+="  "+str(self._FS)

        return tg.strip()


    # .......................
    # Convert the FanzineIssueSpec into the shortest pretty string that identifies the issue
    def IssueDesignation(self) -> str:
        if not self._FS.IsEmpty():
            return str(self._FS)
        if not self._FD.IsEmpty():
            return str(self._FD)
        return ""


    # Two issue designations are deemed to be equal if they are identical or if the VN matches while at least on of the Wholes in None or
    # is the Whole matches and at least one of the Vs and Ns is None.  (We would allow match of (W13, V3, N2) with (W13), etc.)

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

    def DeepCopy(self, other: FanzineIssueSpec) -> None:
        self.Vol=other.Vol
        self.Num=other.Num
        self.NumSuffix=other.NumSuffix
        self.Whole=other.Whole
        self.WSuffix=other.WSuffix
        self.Year=other.Year
        self.Month=other.Month
        self.Day=other.Day
        self.FS.Copy(other.FS)
        self.FD.Copy(other.FD)


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
    def FS(self, val: FanzineSerial) -> None:         # FanzineIssueSpec
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
        print("Setting _FS.Whole to "+str(val))
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
    def Day(self) -> Optional[int]:             # FanzineIssueSpec
        return self._FD.Day

    @Day.setter
    def Day(self, val: Optional[int]) -> None:         # FanzineIssueSpec
        self._FD.Day=val

    # .....................
    @property
    def DayText(self) -> Optional[str]:         # FanzineIssueSpec
        return self._FD.DayText
    # There is no setter; Setting should be done when creating the instance or through the Day setter

    #.....................
    @property
    def DateStr(self) -> str:                   # FanzineIssueSpec
        return str(self._FD)

    @property
    def SerialStr(self) -> str:                  # FanzineIssueSpec
        return str(self._FS)

    # .....................
    # Return a datetime.date object
    def Date(self) -> datetime.date:                     # FanzineIssueSpec
        return self._FD.Date

    #.......................
    def IsEmpty(self) -> bool:                          # FanzineIssueSpec
        return self._FD.IsEmpty() and self._FS.IsEmpty()


    # =====================================================================================
#    def DecodeIssueDesignation(self, s: str) -> None:         # FanzineIssueSpec
#        self._FS.DecodeIssueDesignation(s)


    # =====================================================================================
    # Take the input string and turn it into a FIS
    # The input could be a single date or it could be a single serial ID or it could be a range (e.g., 12-17)
    @classmethod
    def Match(cls, s: str, strict: bool = False, complete: bool=False):                   # FanzineIssueSpec

        # A number standing by itself is messy, since it's easy to confuse with a date
        # In the FanzineIssueSpec world, we will always treat it as a Serial, so look for that first
        m=re.match("^(\d+)$", s)
        if m is not None and len(m.groups()) == 1:
            w=m.groups()[0]
            fs=FanzineSerial(Whole=w)
            return cls(FS=fs)

        # First try a date, and interpret it strictly no matter what the parameter says -- we can try non-strict later
        fd=FanzineDate().Match(s, strict=True, complete=True)
        if not fd.IsEmpty():
            return cls(FD=fd)

        # OK, it's probably not a date.  So try it as a serial ID
        fs=FanzineSerial().Match(s, strict=strict, complete=True)
        if not fs.IsEmpty():
            return cls(FS=fs)

        # That didn't work, either.  Try a non-strict date followed by a non-strict serial
        # OK, it's probably not a date.  So try it as a serial ID
        fs=FanzineSerial().Match(s, complete=complete)
        if not fs.IsEmpty():
            return cls(FS=fs)

        # No good.  Failed.
        return cls()


    # =====================================================================================
    # Look for a FIS in the input string.  Return a tuple of (success, <unmatched text>)
    def Scan(self, s: str, strict: bool=False) -> tuple[bool, str]:        # FanzineIssueSpec
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
#TODO: This can be profitably extended by changing the FISL class to include specific names and editors for each issue, since sometimes
#TODO: a series does not have a consistent set throughout.

class FanzineIssueSpecList:
    def __init__(self, List: Optional[list[FanzineIssueSpec]]=None) -> None:      # FanzineIssueSpecList
        self._List=None
        self.List=List  # Use setter
        pass

    # ...............................
    def AppendIS(self, fanzineIssueSpec: Union[None, FanzineIssueSpec, FanzineIssueSpecList]) -> None:      # FanzineIssueSpecList
        if fanzineIssueSpec is None:
            return
        self.Extend(fanzineIssueSpec)
        return

    # ...............................
    # Basically, this is just a synonym for Extend
    def Append(self, lst: Union[FanzineIssueSpecList, list[FanzineIssueSpec], FanzineIssueSpec, None]) -> FanzineIssueSpecList:      # FanzineIssueSpecList
        return self.Extend(lst)

    # ...............................
    def Extend(self, val: Union[FanzineIssueSpecList, list[FanzineIssueSpec], FanzineIssueSpec, None]) -> FanzineIssueSpecList:      # FanzineIssueSpecList
        if self._List is None:
            self._List=[]

        if isinstance(val, FanzineIssueSpecList):
            lst=val.List
            if lst is None or len(lst) == 0:
                pass      # Nothing to do
            else:
                self._List.extend(lst)
        elif isinstance(val, list):
            if len(val) == 0:
                pass        # Nothing to do
            else:
                self._List.extend(val)
        elif isinstance(val, FanzineIssueSpec):
            self._List.append(val)
        else:
            Exception("FanzineIssueSpecList.Extend: Uninterpretable val type")
        return self

    # ...............................
    def IsEmpty(self) -> bool:      # FanzineIssueSpecList
        if self._List is None or len(self._List) == 0:
            return True
        # Next we go through the elements of the list. If *any* element is non-empty, then the whole FISL is non-empty
        for fis in self._List:
            if not fis.IsEmpty():
                return False
        return True

    # ...............................
    def __repr__(self) -> str:      # FanzineIssueSpecList
        s=""
        if self._List is not None:
            for i in self:
                if len(s) > 0:
                    s=s+",  "
                if i is not None:
                    s=s+repr(i)
                else:
                    s=s+"Missing ISList"
        if len(s) == 0:
            s="Empty ISlist"
        return s


    #...............................
    def __str__(self) -> str:   # Format the ISL for pretty      # FanzineIssueSpecList
        s=""
        for i in self:
            if i is not None:
                if len(s) > 0:
                    s=s+", "
                s=s+str(i)
        return "FISL("+str(len(self._List))+"): "+s

    # ...............................
    def __len__(self) -> int:
        if self._List is None:
            return 0
        return len(self._List)

    # ...............................
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
        if isinstance(val, list):
            if len(val) == 0:
                self._List=[]
                return
            if isinstance(val[0], FanzineIssueSpec):
                self._List=val
                return
        Log("****FanzineIssueSpecList.List setter() had strange input: "+str(val))

    #-----------------------------------
    # Iterators which allow a FanzineIssueSpecList to be iterated directly and not through _List
    def __getitem__(self, key: int) -> FanzineIssueSpec:      # FanzineIssueSpecList
        return self._List[key]

    def __setitem__(self, key: int, value: FanzineIssueSpec) -> FanzineIssueSpecList:      # FanzineIssueSpecList
        self.List[key]=value
        return self


    # =====================================================================================
    # Pull a Serial off of the end of a string, returning a FISL and the remainder of the string
    def GetTrailingSerial(self, s: str) -> tuple[Optional[FanzineIssueSpecList], str]:       # FanzineIssueSpecList
        # Try to greedily (reverse-greedily?) interpret the trailing text as a FanzineIssueSpec.
        # We do this by interpreting more and more tokens starting from the end until we have something that is no longer recognizable as a FanzineIssueSpec
        # The just-previous set of tokens constitutes the full IssueSpec, and the remaining leading tokens are the series name.
        tokens=s.split()  # Split into tokens on spaces
        if len(tokens) == 0:
            return None, s

        leadingText=" ".join(tokens)
        longestFISL=None
        for index in range(len(tokens)-1, -1, -1):  # Ugly, but I need index to be the indexes of the tokens
            trailingText=" ".join(tokens[index:])
            leadingText=" ".join(tokens[:index])
            print("     index="+str(index)+"   leading='"+leadingText+"'    trailing='"+trailingText+"'")
            trialFISL=FanzineIssueSpecList().Match(trailingText, strict=True, complete=True)  # Failed.  We've gone one too far. Quit trying and use what we found on the previous iteration
            if trialFISL.IsEmpty():
                print("     ...backtracking. Found FISL="+repr(trialFISL))
                leadingText=" ".join(tokens[0:index+1])
                break
            longestFISL=trialFISL
        # At this point, leadingText is the fanzine's series name and longestFISL is a list of FanzineSerials found for it
        print("     Found: "+str(longestFISL))
        return longestFISL, leadingText

    #------------------------------------------------------------------------------------
    # Take the input string and turn it into a FISL
    # The input string is a comma-separated list of issue numbers and dates, including ranges:
    # 1, 2, 3, 7, 9-12, 14A, V7#40, VIII, IX, 99, Jan 1999, March 31, 2005, 2007
    # The one place we allow internal commas is in a date where the month/day can be separated from the year by a comma.
    @classmethod
    def Match(cls, s: str, strict: bool=False, complete: bool=False) -> FanzineIssueSpecList:      # FanzineIssueSpecList
        fislist: list[FanzineIssueSpec]=[]      # Accumulate the list of FISs here

        tokens=[t.strip() for t in s.split(",")]        # Split the input on commas

        # The strategy will be to worth through the list of issue information, taking one at a time.
        while len(tokens) > 0:
            # Because some legitimate FISs have an internal comma, they may have been split into two tokens, so we first joing the leading two tokens and see if they make sense
            # If there are at least two tokens left, re-join them and see if the result is an FIS of the form <Month> [day], yyyy
            # We can't allow 2-digit years here because they are indistinguishable from issue numbers.
            if len(tokens) > 1:
                #TODO: We are currently being very conservative in what we recognize here.  This might well be improved.
                # Token 0 must contain a month name as its first token and may not start with a digit
                if not tokens[0][0].isdigit() and MonthNameToInt(tokens[0].split()[0]) is not None:
                    # Token 1 must be a 4-digit year
                    if re.match("^\d{4}$", tokens[1]) is not None:
                        # The put them together and try to interpret as a date
                        trial=tokens[0]+", "+tokens[1]
                        fis=FanzineIssueSpec().Match(trial, strict=True, complete=True)    # This match must consume the entire input -- no partial matches
                        if not fis.IsEmpty():
                            fislist.append(fis)
                            del tokens[0:1]     # Delete both leading tokens.
                            continue

            # Interpreting the first two tokensas one  didn't work, so now try just the first token
            # The first thing to look for is a range denoting multiple issues.  This will necessarily contain a hyphen, which can only appear to denote a range
            # nnn-nnn
            #TODO: Consider also handling date ranges, e.g., Jan-Jun 2001
            if "-" in tokens[0]:
                subtokens=tokens[0].split("-")
                # For now, at least, we can only handle the case of two subtokens, both of which are integers with the first the smaller
                if len(subtokens) != 2:
                    Log("FanzineIssueSpecList:Match: More than one hyphen found in '"+s+"'")
                    return cls()
                if not IsInt(subtokens[0]) or not IsInt(subtokens[1]) or int(subtokens[0]) >= int(subtokens[1]):
                    Log("FanzineIssueSpecList:Match: bad range values in '"+s+"'")
                    return cls()
                for i in range(int(subtokens[0]), int(subtokens[1])+1):
                    fislist.append(FanzineIssueSpec(Whole=i))
                del tokens[0]
                continue

            # It's neither a group including a comma nor a range.  Try to interpret the token as a single FIS
            # Now just look for a single issue
            # nnn or Vnn #nn or variants or dates, etc.
            fis=FanzineIssueSpec().Match(tokens[0], strict=strict, complete=complete)
            if not fis.IsEmpty():
                fislist.append(fis)
                del tokens[0]
                continue

            # Nothing worked, so we won't have an FISL
            Log("FanzineIssueSpecList.Match can't interpret '"+str(tokens[0]+"' as an issue spec.  It is ignored."))
            del tokens[0]

        # We have consumed the whole input.  Return a FISL
        return cls(List=fislist)


    #------------------------------------------------------------------------------------
    # Look for a FISL in the input string.  Return a tuple of (success, <unmatched text>)
    def Scan(self, s: str, strict: bool=False) -> tuple[bool, str]:      # FanzineIssueSpecList
        raise Exception


######################################################################################################################
######################################################################################################################
# FanacIssueInfo
######################################################################################################################
#####################################################################################################################

class FanzineIssueInfo:

    def __init__(self, Series: Optional[FanzineSeriesInfo]=None, IssueName: str="", DisplayName: str="",
                 DirURL: str="", PageFilename: str="", FIS: Optional[FanzineIssueSpec]=None, Position: int=-1,
                 Pagecount: Optional[int]=None, Editor: str="", Country: str="", Taglist: list[str]=None, Mailings: list[str]=None, Temp: any=None, AlphabetizeIndividually: bool=False) -> None:
        _Series: Optional[FanzineSeriesInfo]=None
        _IssueName: str=""      # Name of this issue (does not include issue #/date info)
        _DisplayName: str=""    # Name to use for this issue. Includes issue serial and or date
        _DirURL: str=""  # URL of fanzine directory
        _PageFilename: str=""  # URL of specific issue in directory
        _FIS: Optional[FanzineIssueSpec]=None  # FIS for this issue
        _Position: int=-1        # The index in the source fanzine index table
        _Pagecount: int=0  # Page count for this issue
        _Editor: str=""     # The editor for this issue.  If None, use the editor of the series
        _Locale: Locale
        _Taglist: Optional[list[str]]=None  # A list of tags for this fanzine (e.g., "newszine")
        _Mailings: list[str]=[]  # A List of APA mailings this issue was a part of
        _Temp: any=None     # Used outside the class to hold random information
        _AlphabetizeIndividually: bool=False

        # Use the properties to set the values for all of the instance variables. We do this so that any special setter processing is done with the init values.
        self.Series=Series
        self.IssueName=IssueName
        self.DisplayName=DisplayName
        self.DirURL=DirURL
        self.PageFilename=PageFilename
        self.FIS=FIS
        self._Position=Position
        self.Pagecount=Pagecount
        self.Editor=Editor
        self._Locale=Locale(Country)
        self.Taglist=Taglist
        self.Mailings=Mailings
        self.AlphabetizeIndividually=AlphabetizeIndividually
        self.Temp=Temp

    # .....................
    def __str__(self) -> str:                       # FanzineIssueInfo
        out=""
        if self.DisplayName != "":
            return self.DisplayName

        if self.IssueName != "":
            out=self.IssueName
        elif self.SeriesName != "":
            out=self.SeriesName

        if self.FIS is not None and len(str(self.FIS)) > 0:
            out+=" "+str(self.FIS)

        return out.strip()

    # .....................
    def __repr__(self) -> str:                       # FanzineIssueInfo
        out=""
        if self.DisplayName != "":
            out="'"+self.DisplayName+"'"
        elif self.IssueName != "":
            out=self.IssueName
        elif self.SeriesName != "":
            out=self.SeriesName

        if self.FIS is not None and len(str(self.FIS)) > 0:
            out+=" {"+str(self.FIS)+"}"

        if self.Editor != "":
            out+="  ed:"+self.Editor
        if self.Pagecount is not None:
            out+="  "+str(self.Pagecount)+" pp"

        return out.strip()

    # .....................
    def __eq__(self, other:FanzineIssueInfo) -> bool:                       # FanzineIssueInfo
        if self.SeriesName != other.SeriesName:
            return False
        if self._Editor != other._Editor:
            return False
        if self._IssueName != other._IssueName:
            return False
        if self._DisplayName != other._DisplayName:
            return False
        if self._DirURL != other._DirURL:
            return False
        if self._PageFilename != other._PageFilename:
            return False
        if self._Pagecount != other._Pagecount:
            return False
        if self._FIS is not None and not self._FIS.IsEmpty():
            if other._FIS is None or other._FIS.IsEmpty():
                return False
            if self._FIS != other._FIS:
                return False
        return True


    def DeepCopy(self) -> FanzineIssueInfo:
        fz=FanzineIssueInfo(Series=self.Series, IssueName=self.IssueName, DisplayName=self.DisplayName, DirURL=self.DirURL,
                            PageFilename=self.PageFilename, FIS=self.FIS, Pagecount=self.Pagecount, Editor=self.Editor, Country="",
                            Taglist=None, Mailings=self.Mailings, Temp=self.Temp)
        # Do some touch-ups
        fz._Locale=self.Locale
        fz.Taglist=[x for x in self.Taglist]
        return fz

    # .....................
    def IsEmpty(self) -> bool:                       # FanzineIssueInfo
        if self.SeriesName != "" or self.IssueName != "" or self._DisplayName != "" or self.DirURL != "" or self.PageFilename != "" or self.Pagecount > 0 or self.Editor != "" or self.Taglist or self.Mailings:
            return False
        return self.FIS.IsEmpty()

    # .....................
    @property
    def SeriesName(self) -> str:    # FanzineIssueInfo
        if self._Series is None:
            return ""
        return self._Series.SeriesName
    @SeriesName.setter
    def SeriesName(self, val: str) -> None:                       # FanzineIssueInfo
        assert False

    # .....................
    @property
    def Series(self) -> FanzineSeriesInfo:                       # FanzineIssueInfo
        if self._Series is None:
            self._Series=FanzineSeriesInfo()
        return self._Series
    @Series.setter
    def Series(self, val: Optional[FanzineSeriesInfo]) -> None:                       # FanzineIssueInfo
        self._Series=val

    # .....................
    @property
    def IssueName(self) -> str:                       # FanzineIssueInfo
        return self._IssueName
    @IssueName.setter
    def IssueName(self, val: str) -> None:                       # FanzineIssueInfo
        self._IssueName=val.strip()

    # .....................
    @property
    def DisplayName(self) -> str:                       # FanzineIssueInfo
        if self._DisplayName != "":
            return self._DisplayName
        if self.FIS is not None and self.SeriesName != "":
            return self.SeriesName+" "+str(self.FIS)
        return self.SeriesName
    @DisplayName.setter
    def DisplayName(self, val: str) -> None:                       # FanzineIssueInfo
        self._DisplayName=val.strip()

    # .....................
    @property
    def DirURL(self) -> str:                       # FanzineIssueInfo
        return self._DirURL
    @DirURL.setter
    def DirURL(self, val: str) -> None:                       # FanzineIssueInfo
        self._DirURL=val

    # .....................
    @property
    def PageFilename(self) -> str:                       # FanzineIssueInfo
        return self._PageFilename
    @PageFilename.setter
    def PageFilename(self, val: str) -> None:                       # FanzineIssueInfo
        self._PageFilename=val.strip()

    # .....................
    @property
    def URL(self) -> str:                       # FanzineIssueInfo
        return self.DirURL+"/"+self.PageFilename

    # .....................
    @property
    def Temp(self) -> any:                       # FanzineIssueInfo
        return self._Temp
    @Temp.setter
    def Temp(self, val: any) -> None:                       # FanzineIssueInfo
        self._Temp=val

    # .....................
    @property
    def FIS(self) -> Optional[FanzineIssueSpec]:                       # FanzineIssueInfo
        return self._FIS
    @FIS.setter
    def FIS(self, val: FanzineIssueSpec) -> None:                       # FanzineIssueInfo
        self._FIS=val

    # .....................
    @property
    def Position(self) -> Optional[int]:                       # FanzineIssueInfo
        return self._Position
    @Position.setter
    def Position(self, val: int) -> None:                       # FanzineIssueInfo
        self._Position=val

    # .....................
    @property
    def Locale(self) -> Locale:                       # FanzineIssueInfo
        return self._Locale
    # @Locale.setter
    # def Locale(self, val: FanzineIssueSpec) -> None:                       # FanzineIssueInfo
    #     self._Locale=val

    # .....................
    @property
    def Pagecount(self) -> int:                       # FanzineIssueInfo
        return self._Pagecount if self._Pagecount > 0 else 1
    @Pagecount.setter
    def Pagecount(self, val: int) -> None:                       # FanzineIssueInfo
        self._Pagecount=val

    # .....................
    @property
    def Editor(self) -> str:                       # FanzineIssueInfo
        return self._Editor
    @Editor.setter
    def Editor(self, val: str) -> None:                       # FanzineIssueInfo
        self._Editor=val

    # .....................
    @property
    def SeriesEditor(self) -> str:
        if self._Series.Editor is not None:
            return self._Series.Editor
        return self.Editor


    # .....................
    @property
    def Taglist(self) -> list[str]:  # FanzineIssueInfo
        return self._Taglist

    @Taglist.setter
    def Taglist(self, val: list[str]) -> None:  # FanzineIssueInfo
        if val is None:
            val=[]
        self._Taglist=val

    # .....................
    @property
    def Mailings(self) -> list[str]:  # FanzineIssueInfo
        return self._Mailings
    @Mailings.setter
    def Mailings(self, val: list[str]) -> None:  # FanzineIssueInfo
        if val is None:
            val=[]
        self._Mailings=val

    # .....................
    @property
    def AlphabetizeIndividually(self) -> bool:  # FanzineIssueInfo
        return self._AlphabetizeIndividually
    @AlphabetizeIndividually.setter
    def AlphabetizeIndividually(self, val: bool) -> None:  # FanzineIssueInfo
        if val is None:
            val=[]
        self._AlphabetizeIndividually=val

######################################################################################################################
######################################################################################################################
# FanzineSeriesList
######################################################################################################################
#####################################################################################################################

# This is a class used to hold a list of many issues of a single fanzine.
class FanzineSeriesList:

    def __init__(self)  -> None:
        self._FIIL: Optional[list[FanzineIssueInfo]]=[]
        self._SeriesName: str=""
        self._Editor: str=""
        self._Eligible: Optional[bool]=None     # Is this eligible for the Hugos in a year in question?
        self._Notes: str=""
        self._SeriesURL: str=""

    # .....................
    @property
    def SeriesName(self) -> str:            # FanzineSeriesList
        return self._SeriesName
    @SeriesName.setter
    def SeriesName(self, val: str) -> None:            # FanzineSeriesList
        self._SeriesName=val.strip()

    # .....................
    @property
    def Editor(self) -> str:            # FanzineSeriesList
        return self._Editor

    @Editor.setter
    def Editor(self, val: str) -> None:            # FanzineSeriesList
        self._Editor=val

    # .....................
    @property
    def Eligible(self) -> bool:            # FanzineSeriesList
        if self._Eligible is None:
            return False
        return self._Eligible

    @Eligible.setter
    def Eligible(self, val: Optional[bool]) -> None:            # FanzineSeriesList
        self._Eligible=val

    # .....................
    @property
    def FIIL(self) -> Optional[list[FanzineIssueInfo]]:            # FanzineSeriesList
        #TODO: If we're returning an FIIL independent of the FSL, shouldn't we fill in the values which would be gotten by reference to the FSL?
        return self._FIIL

    @FIIL.setter
    def FIIL(self, val: Optional[FanzineIssueSpecList]) -> None:            # FanzineSeriesList
        # If there is no existing list of FIIs, we create one from the FISL
        if self._FIIL is not None and len(self._FIIL) > 0:
            raise(Exception("FIIL setter: FIIL is non-empty"))
        self._FIIL=[]
        for el in val:
            self._FIIL.append(FanzineIssueInfo(FIS=el, Editor=self.Editor, DirURL=self.SeriesURL))

    # .....................
    @property
    def Notes(self) -> str:            # FanzineSeriesList
        return self._Notes

    @Notes.setter
    def Notes(self, val: str) -> None:            # FanzineSeriesList
        self._Notes=val.strip()

    # .....................
    @property
    def SeriesURL(self) -> str:            # FanzineSeriesList
        return self._SeriesURL

    @SeriesURL.setter
    def SeriesURL(self, val: str) -> None:            # FanzineSeriesList
        self._SeriesURL=val.strip()

    # .....................
    def __repr__(self) -> str:  # Convert the FSS into a debugging form            # FanzineSeriesList
        iil="-"
        if len(self._FIIL) > 0:
            iil=repr(self._FIIL)

        sn="-"
        if self._SeriesName != "":
            sn=self._SeriesName+" "

        ed="-"
        if self._Editor != "":
            ed=self._Editor+" "

        nt=""
        if self._Notes != "":
            nt+=self._Notes+" "

        el="-"
        if self._Eligible is not None:
            el="T" if self._Eligible else "F"+" "

        u="-"
        if self._SeriesURL != "":
            u=self._SeriesURL

        return "FSS(SN:"+sn+", IIL:"+iil+", Ed:"+ed+", NT:"+nt+", El:"+el+" URL="+u+")"

    # .....................
    def __str__(self) -> str:  # Pretty print the FSS            # FanzineSeriesList
        out=""
        if self.SeriesName != "":
            out=self.SeriesName

        if self._Editor != "":
            out+=f"   ({self._Editor})"

        if self._Notes != "":
            out+=f"   ({self._Notes}) "

        if self._FIIL is not None and len(self._FIIL) > 0:
            out+="  FIIL: "
            for i in self._FIIL:
                if not i.IsEmpty():
                    out+=str(i)+", "
        return out


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
def InterpretNamedDay(dayString: str) -> Optional[tuple[int, int]]:
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
        "Late february or early march": (3, None),
        "ides of march": (3, 15),
        "st urho's day": (3, 16),
        "st. urho's day": (3, 16),
        "saint urho's day": (3, 16),
        "vernal equinox": (3, 20),
        "spring equinox": (3, 20),
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
        return namedDayConverstionTable[dayString.lower().replace(",", "")]

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
    return 0 < d <= monthlength


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
def BoundDay(d: Optional[int], m: Optional[int], y: Optional[int]) -> tuple[Optional[int], Optional[int], Optional[int]]:
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


# =================================================================================
# Deal with things of the form "June 20," and "20 June" and just "June"
# Return a tuple of (month, day)
# (Day defaults to 1 if no day was supplied.)
def InterpretMonthDay(s: str) -> Optional[tuple[int, Optional[int]]]:
    s=s.strip() # Get rid of leading and traling blanks as they can't possibly be of interest
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

    # If it ends in a "." it may be abbreviated. Remove trailing "."
    monthData=monthData.removesuffix(".")

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
def InterpretRandomDatestring(text: str) -> Optional[FanzineDate]:
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
        ser=FanzineSerial().Match(volNumText)
        if ser.Vol is not None and ser.Num is not None:  # Otherwise, we don't actually have a volume+number
            volInt=ser.Vol
            numInt=ser.Num
            numsuffix=ser.NumSuffix

    if volText is not None:
        volInt=InterpretInteger(volText)

    # If there's no vol, anything under "Num", etc., must actually be a whole number
    if volText is None:
        with suppress(Exception):
            maybeWholeText=numText
            maybeWholeInt=int(maybeWholeText)
            numText=None

    # But if there *is* a volume specified, than any number not labelled "whole" must be a number within the volume
    if volText is not None and numText is not None:
        numInt=InterpretInteger(numText)

    # OK, now figure out the vol, num and whole.
    # First, if a Vol is present, and an unambigious Num is absent, the an ambigious Num must be the Vol's num
    if volInt is not None and numInt is None and maybeWholeInt is not None:
        numInt=maybeWholeInt
        maybeWholeInt=None

    # If the wholeInt is missing and maybeWholeInt hasn't been used up, make it the wholeInt
    if wholeInt is None and maybeWholeInt is not None:
        wholeInt=maybeWholeInt

    # Next, look at the title -- titles often have a serial designation at their end.

    if titleText is not None:
        # Possible formats:
        #   n   -- a whole number
        #   n.m -- a decimal number
        #   Vn  -- a volume number, but where's the issue?
        #   Vn[,] #m  -- a volume and number-within-volume
        #   Vn.m -- ditto
        ser=FanzineSerial().Match(titleText if type(titleText) is not list else titleText[0])

        # Some indexes have fanzine names ending in <month> <year>.  We'll detect these by looking for a trailing number between 1930 and 2050, and reject
        # getting vol/ser, etc., from the title if we find it.
        if ser.Num is None or ser.Num < 1930 or ser.Num > 2050:

            if ser.Vol is not None and ser.Num is not None:
                if volInt is None:
                    volInt=ser.Vol
                if numInt is None:
                    numInt=ser.Num

                if volInt != ser.Vol:
                    LogError("***Inconsistent serial designations: Volume='"+str(volInt)+"' which is not Vol='"+str(ser.Vol)+"'")
                if numInt != ser.Num:
                    LogError("***Inconsistent serial designations: Number='"+str(numInt)+"' which is not Num='"+str(ser.Num)+"'")

            elif ser.Num is not None:
                if wholeInt is None:
                    wholeInt=ser.Num

                if wholeInt != ser.Num:
                    LogError("***Inconsistent serial designations: Whole='"+str(wholeInt)+"'  which is not Num='"+str(ser.Num)+"'")

            if ser.Whole is not None:
                wholeInt=ser.Whole

            numsuffix=ser.NumSuffix
            wsuffix=ser.WSuffix

    return FanzineSerial(Vol=volInt, Num=numInt, NumSuffix=numsuffix, Whole=wholeInt, WSuffix=wsuffix)


