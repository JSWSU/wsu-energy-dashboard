Attribute VB_Name = "ExportDataJSON"
Option Explicit

' =====================================================================
' ExportDataJSON - Exports data from the CORRECT "Executive Summary (Print)"
' sheet, HDD Data, Kintec Data, and cross-checks against Consolidated Data.
'
' Reads from: Executive Summary (Print), HDD Data, Kintec Data, Consolidated Data
' Writes to:  data.json (same folder as workbook)
'
' Usage: Click the "Export Data" button on Executive Summary (Print),
'        or run ExportDataJSON from the Macros menu (Alt+F8).
' =====================================================================

Public Sub ExportDataJSON()
    On Error GoTo ErrHandler

    Dim wsExec As Worksheet
    Dim wsHDD As Worksheet
    Dim wsKintec As Worksheet
    Dim wsConsol As Worksheet
    Dim json As String
    Dim filePath As String
    Dim fNum As Integer
    Dim i As Long
    Dim warnings As String

    Application.StatusBar = "Exporting data.json..."
    Application.ScreenUpdating = False

    Set wsExec = ThisWorkbook.Sheets("Executive Summary (Print)")
    Set wsHDD = ThisWorkbook.Sheets("HDD Data")
    Set wsKintec = ThisWorkbook.Sheets("Kintec Data")
    Set wsConsol = ThisWorkbook.Sheets("Consolidated Data")

    warnings = ""

    ' Build the JSON string
    json = "{" & vbCrLf

    ' --- Last Updated ---
    json = json & "  ""lastUpdated"": """ & Format(Now, "mmmm d, yyyy") & """," & vbCrLf

    ' =================================================================
    ' FY2026 ACTUALS / FORECASTS  (Exec Summary Print rows 3-14)
    ' Row 2 = header, Rows 3-14 = Jul 2025 through Jun 2026
    ' Col B=Total Actual, C=Elec Actual, D=Gas Actual
    ' Col E=Total Fcast, F=Elec Fcast, G=Gas Fcast Total
    ' Col H=Kintec Gas Fcast, I=Avista Gas Fcast
    ' Col J=NG Tariff %, Col K=Price Hedge %
    ' =================================================================
    json = json & "  ""fy26"": {" & vbCrLf
    json = json & "    ""totalActual"": [" & ReadRow(wsExec, 3, 14, 2) & "]," & vbCrLf
    json = json & "    ""elecActual"": [" & ReadRow(wsExec, 3, 14, 3) & "]," & vbCrLf
    json = json & "    ""gasActual"": [" & ReadRow(wsExec, 3, 14, 4) & "]," & vbCrLf
    json = json & "    ""totalFcast"": [" & ReadRow(wsExec, 3, 14, 5) & "]," & vbCrLf
    json = json & "    ""elecFcast"": [" & ReadRow(wsExec, 3, 14, 6) & "]," & vbCrLf
    json = json & "    ""gasFcast"": [" & ReadRow(wsExec, 3, 14, 7) & "]," & vbCrLf
    json = json & "    ""kintecFcast"": [" & ReadRow(wsExec, 3, 14, 8) & "]," & vbCrLf
    json = json & "    ""avistaFcast"": [" & ReadRow(wsExec, 3, 14, 9) & "]," & vbCrLf
    ' Hedge is in col K (11); check if stored as decimal or already %
    Dim hedgeVal As Double
    hedgeVal = wsExec.Cells(3, 11).Value
    If hedgeVal < 1 And hedgeVal > 0 Then hedgeVal = hedgeVal * 100
    json = json & "    ""hedge"": " & Format(hedgeVal, "0.0") & vbCrLf
    json = json & "  }," & vbCrLf

    ' =================================================================
    ' FY2025 GAS  (Exec Summary Print rows 21-32)
    ' Row 20 = header, Rows 21-32 = Jul 2024 through Jun 2025
    ' Col B=Gas Cost Actual, C=Gas MMBTU Actual, D=Gas $/MMBTU Actual
    ' Col E=Gas Cost Fcast, F=Gas MMBTU Fcast, G=Gas $/MMBTU Fcast
    ' Col H=Kintec $, Col I=Avista $
    ' =================================================================
    json = json & "  ""fy25gas"": {" & vbCrLf
    json = json & "    ""cost"": [" & ReadRow(wsExec, 21, 32, 2) & "]," & vbCrLf
    json = json & "    ""mmbtu"": [" & ReadRow(wsExec, 21, 32, 3) & "]," & vbCrLf
    json = json & "    ""perUnit"": [" & ReadRowDec(wsExec, 21, 32, 4, 2) & "]," & vbCrLf
    json = json & "    ""kintec"": [" & ReadRow(wsExec, 21, 32, 8) & "]," & vbCrLf
    json = json & "    ""avista"": [" & ReadRow(wsExec, 21, 32, 9) & "]" & vbCrLf
    json = json & "  }," & vbCrLf

    ' =================================================================
    ' FY2026 ENERGY USE  (Exec Summary Print rows 39-50)
    ' Row 38 = header, Rows 39-50 = Jul 2025 through Jun 2026
    ' Col B=Total MMBTU Actual, C=Elec MMBTU Actual, D=Gas MMBTU Actual
    ' Col E=Total MMBTU Fcast, F=Elec MMBTU Fcast, G=Gas MMBTU Fcast
    ' Col H=Total kWh Actual, Col I=Total kWh Fcast, Col J=kWh $/Unit
    ' =================================================================
    json = json & "  ""energyUse"": {" & vbCrLf
    json = json & "    ""totalActual"": [" & ReadRow(wsExec, 39, 50, 2) & "]," & vbCrLf
    json = json & "    ""elecActual"": [" & ReadRow(wsExec, 39, 50, 3) & "]," & vbCrLf
    json = json & "    ""gasActual"": [" & ReadRow(wsExec, 39, 50, 4) & "]," & vbCrLf
    json = json & "    ""totalFcast"": [" & ReadRow(wsExec, 39, 50, 5) & "]," & vbCrLf
    json = json & "    ""kwhActual"": [" & ReadRow(wsExec, 39, 50, 8) & "]," & vbCrLf
    json = json & "    ""kwhRate"": [" & ReadRowDec(wsExec, 39, 50, 10, 4) & "]" & vbCrLf
    json = json & "  }," & vbCrLf

    ' =================================================================
    ' YEAR-OVER-YEAR MMBTU  (Exec Summary Print rows 57-68)
    ' Row 56 = header, Rows 57-68 = Jul through Jun
    ' This sheet only has FY2025 and FY2026 (2 years, not 3)
    ' Col B=FY25 Total, C=FY25 Elec, D=FY25 Gas
    ' Col E=FY26 Total, F=FY26 Elec, G=FY26 Gas
    ' =================================================================
    json = json & "  ""yoy"": {" & vbCrLf
    json = json & "    ""fy25total"": [" & ReadRow(wsExec, 57, 68, 2) & "]," & vbCrLf
    json = json & "    ""fy25elec"": [" & ReadRow(wsExec, 57, 68, 3) & "]," & vbCrLf
    json = json & "    ""fy25gas"": [" & ReadRow(wsExec, 57, 68, 4) & "]," & vbCrLf
    json = json & "    ""fy26total"": [" & ReadRow(wsExec, 57, 68, 5) & "]," & vbCrLf
    json = json & "    ""fy26elec"": [" & ReadRow(wsExec, 57, 68, 6) & "]," & vbCrLf
    json = json & "    ""fy26gas"": [" & ReadRow(wsExec, 57, 68, 7) & "]" & vbCrLf
    json = json & "  }," & vbCrLf

    ' =================================================================
    ' CUMULATIVE SUMMARY  (Exec Summary Print rows 74-85)
    ' Row 73 = header, Rows 74-85 = Jul 2025 through Jun 2026
    ' Col B=Total Energy $ Actual, C=Total Energy $ Forecast
    ' Col D=Delta ($), Col E=Delta (%), Col F=Total MMBTU Actual
    ' Col G=Total MMBTU Forecast, Col H=Delta MMBTU, Col I=Delta MMBTU %
    ' =================================================================
    json = json & "  ""cumul"": {" & vbCrLf
    json = json & "    ""actual"": [" & ReadRow(wsExec, 74, 85, 2) & "]," & vbCrLf
    json = json & "    ""forecast"": [" & ReadRow(wsExec, 74, 85, 3) & "]," & vbCrLf
    json = json & "    ""delta"": [" & ReadRow(wsExec, 74, 85, 4) & "]," & vbCrLf
    json = json & "    ""deltaPct"": [" & ReadRowPct(wsExec, 74, 85, 5) & "]," & vbCrLf
    json = json & "    ""mmbtuAct"": [" & ReadRow(wsExec, 74, 85, 6) & "]," & vbCrLf
    json = json & "    ""mmbtuFcast"": [" & ReadRow(wsExec, 74, 85, 7) & "]," & vbCrLf
    json = json & "    ""mmbtuDelta"": [" & ReadRow(wsExec, 74, 85, 8) & "]," & vbCrLf
    json = json & "    ""mmbtuDeltaPct"": [" & ReadRowPct(wsExec, 74, 85, 9) & "]" & vbCrLf
    json = json & "  }," & vbCrLf

    ' =================================================================
    ' PRICE vs VOLUME VARIANCE  (Exec Summary Print rows 127-138)
    ' Row 126 = header, Rows 127-138 = Jul through Jun
    ' Col B=FY25 Total Cost, C=FY26 Total Cost, D=Total $ Variance
    ' Col E=FY25 MMBTU, F=FY26 MMBTU, G=Volume Var MMBTU, H=MMBTU Delta %
    ' Col I=FY25 HDD, J=FY26 HDD, K=HDD Delta %, L=30-Yr Normal HDD
    ' =================================================================
    json = json & "  ""variance"": {" & vbCrLf
    json = json & "    ""fy25cost"": [" & ReadRow(wsExec, 127, 138, 2) & "]," & vbCrLf
    json = json & "    ""fy26cost"": [" & ReadRow(wsExec, 127, 138, 3) & "]," & vbCrLf
    json = json & "    ""costDelta"": [" & ReadRow(wsExec, 127, 138, 4) & "]," & vbCrLf
    json = json & "    ""fy25mmbtu"": [" & ReadRow(wsExec, 127, 138, 5) & "]," & vbCrLf
    json = json & "    ""fy26mmbtu"": [" & ReadRow(wsExec, 127, 138, 6) & "]," & vbCrLf
    json = json & "    ""mmbtuDelta"": [" & ReadRow(wsExec, 127, 138, 7) & "]," & vbCrLf
    json = json & "    ""mmbtuDeltaPct"": [" & ReadRowPct(wsExec, 127, 138, 8) & "]," & vbCrLf
    json = json & "    ""fy25hdd"": [" & ReadRow(wsExec, 127, 138, 9) & "]," & vbCrLf
    json = json & "    ""fy26hdd"": [" & ReadRow(wsExec, 127, 138, 10) & "]," & vbCrLf
    json = json & "    ""hddDeltaPct"": [" & ReadRowPctText(wsExec, 127, 138, 11) & "]," & vbCrLf
    json = json & "    ""normalHdd"": [" & ReadRow(wsExec, 127, 138, 12) & "]" & vbCrLf
    json = json & "  }," & vbCrLf

    ' =================================================================
    ' HDD DATA  (HDD Data sheet rows 6-17, cols C-E)
    ' Row 5 = header, Rows 6-17 = Jul through Jun
    ' Col C=FY25 HDD, Col D=FY26 HDD, Col E=30-Yr Normal
    ' =================================================================
    json = json & "  ""hdd"": {" & vbCrLf
    json = json & "    ""fy25"": [" & ReadRow(wsHDD, 6, 17, 3) & "]," & vbCrLf
    json = json & "    ""fy26"": [" & ReadRow(wsHDD, 6, 17, 4) & "]," & vbCrLf
    json = json & "    ""normal"": [" & ReadRow(wsHDD, 6, 17, 5) & "]" & vbCrLf
    json = json & "  }," & vbCrLf

    ' =================================================================
    ' KINTEC DATA  (Kintec Data sheet, variable rows)
    ' Col A=Invoicing Month, Col E=Total Bill Amount, Col F=Total Usage (Dths)
    ' =================================================================
    Dim lastRow As Long
    lastRow = wsKintec.Cells(wsKintec.Rows.Count, 1).End(xlUp).Row

    Dim monthsStr As String, dthsStr As String, costStr As String
    monthsStr = ""
    dthsStr = ""
    costStr = ""

    For i = 2 To lastRow
        If wsKintec.Cells(i, 1).Value <> "" Then
            Dim dt As Date
            dt = wsKintec.Cells(i, 1).Value
            Dim monLabel As String
            monLabel = Format(dt, "mmm") & "-" & Format(dt, "yy")

            If Len(monthsStr) > 0 Then
                monthsStr = monthsStr & ","
                dthsStr = dthsStr & ","
                costStr = costStr & ","
            End If

            monthsStr = monthsStr & """" & monLabel & """"
            dthsStr = dthsStr & CLng(wsKintec.Cells(i, 6).Value)
            costStr = costStr & CLng(wsKintec.Cells(i, 5).Value)
        End If
    Next i

    json = json & "  ""kintec"": {" & vbCrLf
    json = json & "    ""months"": [" & monthsStr & "]," & vbCrLf
    json = json & "    ""dths"": [" & dthsStr & "]," & vbCrLf
    json = json & "    ""cost"": [" & costStr & "]" & vbCrLf
    json = json & "  }," & vbCrLf

    ' =================================================================
    ' VERIFICATION: Cross-check Consolidated Data against Exec Summary
    ' Sum Electric $, Gas $, kWh, Elec MMBTU, Gas MMBTU by FY26 month
    ' =================================================================
    Dim consolLastRow As Long
    consolLastRow = wsConsol.Cells(wsConsol.Rows.Count, 1).End(xlUp).Row

    ' FY2026 months: Jul 2025 (month 7/2025) through Jun 2026 (month 6/2026)
    Dim fy26Months(1 To 12) As Date
    fy26Months(1) = DateSerial(2025, 7, 1)
    fy26Months(2) = DateSerial(2025, 8, 1)
    fy26Months(3) = DateSerial(2025, 9, 1)
    fy26Months(4) = DateSerial(2025, 10, 1)
    fy26Months(5) = DateSerial(2025, 11, 1)
    fy26Months(6) = DateSerial(2025, 12, 1)
    fy26Months(7) = DateSerial(2026, 1, 1)
    fy26Months(8) = DateSerial(2026, 2, 1)
    fy26Months(9) = DateSerial(2026, 3, 1)
    fy26Months(10) = DateSerial(2026, 4, 1)
    fy26Months(11) = DateSerial(2026, 5, 1)
    fy26Months(12) = DateSerial(2026, 6, 1)

    ' Accumulators: elec$, gas$, kWh, elecMMBTU, gasMMBTU per month
    Dim cElec(1 To 12) As Double
    Dim cGas(1 To 12) As Double
    Dim cKwh(1 To 12) As Double
    Dim cElecMM(1 To 12) As Double
    Dim cGasMM(1 To 12) As Double

    Dim r As Long, m As Long
    Dim rowDate As Variant
    Dim rowSrc As String

    For r = 2 To consolLastRow
        rowSrc = CStr(wsConsol.Cells(r, 1).Value)
        If rowSrc = "" Then GoTo NextConsolRow

        rowDate = wsConsol.Cells(r, 14).Value  ' Month-Year column
        If Not IsDate(rowDate) Then GoTo NextConsolRow

        ' Match to FY26 month index
        For m = 1 To 12
            If CLng(CDate(rowDate)) = CLng(fy26Months(m)) Then
                cElec(m) = cElec(m) + Val(CStr(wsConsol.Cells(r, 10).Value))   ' Electric $
                cGas(m) = cGas(m) + Val(CStr(wsConsol.Cells(r, 11).Value))     ' Gas $
                cKwh(m) = cKwh(m) + Val(CStr(wsConsol.Cells(r, 8).Value))      ' kWh
                cElecMM(m) = cElecMM(m) + Val(CStr(wsConsol.Cells(r, 15).Value)) ' Elec MMBTU
                cGasMM(m) = cGasMM(m) + Val(CStr(wsConsol.Cells(r, 16).Value))   ' Gas MMBTU
                Exit For
            End If
        Next m
NextConsolRow:
    Next r

    ' Build verification JSON
    json = json & "  ""verification"": {" & vbCrLf
    json = json & "    ""source"": ""Consolidated Data""," & vbCrLf
    json = json & "    ""elecDollar"": [" & ArrToStr(cElec) & "]," & vbCrLf
    json = json & "    ""gasDollar"": [" & ArrToStr(cGas) & "]," & vbCrLf
    json = json & "    ""kwh"": [" & ArrToStr(cKwh) & "]," & vbCrLf
    json = json & "    ""elecMmbtu"": [" & ArrToStr(cElecMM) & "]," & vbCrLf
    json = json & "    ""gasMmbtu"": [" & ArrToStr(cGasMM) & "]" & vbCrLf
    json = json & "  }" & vbCrLf

    json = json & "}"

    ' --- Check for discrepancies (only months with Consolidated Data) ---
    ' Consolidated Data only contains billing records for months already invoiced.
    ' Forecast-only months will have $0 in Consolidated Data, so we skip those.
    Dim execMonthTotal As Double, consolMonthTotal As Double
    Dim monthsCompared As Long, monthsWithDiscrepancy As Long
    Dim discrepancyDetail As String
    monthsCompared = 0
    monthsWithDiscrepancy = 0
    discrepancyDetail = ""

    Dim monthNames(1 To 12) As String
    monthNames(1) = "Jul": monthNames(2) = "Aug": monthNames(3) = "Sep"
    monthNames(4) = "Oct": monthNames(5) = "Nov": monthNames(6) = "Dec"
    monthNames(7) = "Jan": monthNames(8) = "Feb": monthNames(9) = "Mar"
    monthNames(10) = "Apr": monthNames(11) = "May": monthNames(12) = "Jun"

    For m = 1 To 12
        consolMonthTotal = cElec(m) + cGas(m)
        ' Only compare months where Consolidated Data has actual billing records
        If consolMonthTotal > 0 Then
            execMonthTotal = CDbl(wsExec.Cells(m + 2, 3).Value) + CDbl(wsExec.Cells(m + 2, 4).Value)
            monthsCompared = monthsCompared + 1
            If execMonthTotal > 0 Then
                Dim pctDiff As Double
                pctDiff = Abs(execMonthTotal - consolMonthTotal) / execMonthTotal * 100
                If pctDiff > 5 Then
                    monthsWithDiscrepancy = monthsWithDiscrepancy + 1
                    discrepancyDetail = discrepancyDetail & "  " & monthNames(m) & ": Exec=$" & _
                        Format(execMonthTotal, "#,##0") & " vs Consol=$" & _
                        Format(consolMonthTotal, "#,##0") & " (" & Format(pctDiff, "0.0") & "%)" & vbCrLf
                End If
            End If
        End If
    Next m

    If monthsWithDiscrepancy > 0 Then
        warnings = warnings & monthsWithDiscrepancy & " of " & monthsCompared & _
                   " month(s) with billing data have >5% discrepancy:" & vbCrLf & discrepancyDetail & _
                   "NOTE: Minor differences are expected. The Executive Summary may include " & _
                   "adjustments, credits, or rounding not reflected in raw Consolidated Data." & vbCrLf
    End If

    ' Write the file
    filePath = ThisWorkbook.Path & "\data.json"
    fNum = FreeFile
    Open filePath For Output As #fNum
    Print #fNum, json
    Close #fNum

    Application.StatusBar = False
    Application.ScreenUpdating = True

    Dim msg As String
    msg = "Export complete!" & vbCrLf & vbCrLf & _
          "data.json saved to:" & vbCrLf & filePath & vbCrLf & vbCrLf & _
          "Upload this file to your GitHub repo to update the web app."

    ' Add verification summary
    Dim verifyMsg As String
    If monthsCompared > 0 Then
        verifyMsg = "Verification: " & monthsCompared & " month(s) with billing data cross-checked " & _
                    "against Consolidated Data."
    Else
        verifyMsg = "Verification: No months with Consolidated Data found for FY2026."
    End If

    If Len(warnings) > 0 Then
        msg = msg & vbCrLf & vbCrLf & verifyMsg & vbCrLf & vbCrLf & _
              "DISCREPANCIES (>5% threshold):" & vbCrLf & warnings
        MsgBox msg, vbExclamation, "Energy Web App Export"
    Else
        msg = msg & vbCrLf & vbCrLf & verifyMsg & vbCrLf & _
              "All months within tolerance. Minor differences between Executive Summary " & _
              "and Consolidated Data are normal (adjustments, credits, rounding)."
        MsgBox msg, vbInformation, "Energy Web App Export"
    End If
    Exit Sub

ErrHandler:
    Application.StatusBar = False
    Application.ScreenUpdating = True
    MsgBox "Export failed at row/step:" & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbCritical, "Export Error"
End Sub

' -----------------------------------------------------------------
' Helper: Read a column across rows, return comma-separated integers
' -----------------------------------------------------------------
Private Function ReadRow(ws As Worksheet, startRow As Long, endRow As Long, col As Long) As String
    Dim result As String
    Dim r As Long
    Dim v As Variant
    result = ""
    For r = startRow To endRow
        If r > startRow Then result = result & ","
        v = ws.Cells(r, col).Value
        If IsNumeric(v) And Not IsEmpty(v) Then
            result = result & CLng(CDbl(v))
        Else
            result = result & "0"
        End If
    Next r
    ReadRow = result
End Function

' -----------------------------------------------------------------
' Helper: Read a column across rows, return comma-separated decimals
' -----------------------------------------------------------------
Private Function ReadRowDec(ws As Worksheet, startRow As Long, endRow As Long, col As Long, decimals As Long) As String
    Dim result As String
    Dim r As Long
    Dim fmt As String
    Dim v As Variant
    fmt = "0." & String(decimals, "0")
    result = ""
    For r = startRow To endRow
        If r > startRow Then result = result & ","
        v = ws.Cells(r, col).Value
        If IsNumeric(v) And Not IsEmpty(v) Then
            result = result & Format(CDbl(v), fmt)
        Else
            result = result & Format(0, fmt)
        End If
    Next r
    ReadRowDec = result
End Function

' -----------------------------------------------------------------
' Helper: Read percentage column - checks cell format to determine
' if value needs *100 conversion
' -----------------------------------------------------------------
Private Function ReadRowPct(ws As Worksheet, startRow As Long, endRow As Long, col As Long) As String
    Dim result As String
    Dim r As Long
    Dim v As Variant
    Dim dVal As Double
    result = ""
    For r = startRow To endRow
        If r > startRow Then result = result & ","
        v = ws.Cells(r, col).Value
        If IsNumeric(v) And Not IsEmpty(v) Then
            dVal = CDbl(v)
            ' If cell is formatted as %, Excel stores 8.7% as 0.087
            If InStr(ws.Cells(r, col).NumberFormat, "%") > 0 Then
                dVal = dVal * 100
            ElseIf Abs(dVal) < 1 And dVal <> 0 Then
                dVal = dVal * 100
            End If
            result = result & Format(dVal, "0.0")
        Else
            result = result & "0"
        End If
    Next r
    ReadRowPct = result
End Function

' -----------------------------------------------------------------
' Helper: Read percentage stored as text like "350%", "(94%)", "(6%)"
' Returns the numeric value (e.g. 350, -94, -6)
' -----------------------------------------------------------------
Private Function ReadRowPctText(ws As Worksheet, startRow As Long, endRow As Long, col As Long) As String
    Dim result As String
    Dim r As Long
    Dim v As Variant
    Dim txt As String
    Dim dVal As Double
    result = ""
    For r = startRow To endRow
        If r > startRow Then result = result & ","
        v = ws.Cells(r, col).Value
        If IsNumeric(v) And Not IsEmpty(v) Then
            dVal = CDbl(v)
            If InStr(ws.Cells(r, col).NumberFormat, "%") > 0 Then
                dVal = dVal * 100
            ElseIf Abs(dVal) < 1 And dVal <> 0 Then
                dVal = dVal * 100
            End If
            result = result & Format(dVal, "0")
        Else
            ' Try parsing text like "(53%)" or "350%"
            txt = CStr(ws.Cells(r, col).Text)
            txt = Replace(txt, "%", "")
            txt = Replace(txt, ",", "")
            If Left(txt, 1) = "(" And Right(txt, 1) = ")" Then
                txt = "-" & Mid(txt, 2, Len(txt) - 2)
            End If
            If IsNumeric(txt) Then
                result = result & CLng(CDbl(txt))
            Else
                result = result & "0"
            End If
        End If
    Next r
    ReadRowPctText = result
End Function

' -----------------------------------------------------------------
' Helper: Convert a Double(1 To 12) array to comma-separated string
' -----------------------------------------------------------------
Private Function ArrToStr(arr() As Double) As String
    Dim result As String
    Dim m As Long
    result = ""
    For m = 1 To 12
        If m > 1 Then result = result & ","
        result = result & CLng(arr(m))
    Next m
    ArrToStr = result
End Function

' =====================================================================
' AddExportButton - Run ONCE to add a clickable button to the
' "Executive Summary (Print)" sheet
' =====================================================================
Public Sub AddExportButton()
    On Error GoTo BtnErr

    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets("Executive Summary (Print)")

    ' Delete existing button if present
    Dim shp As Shape
    For Each shp In ws.Shapes
        If shp.Name = "btnExportJSON" Then shp.Delete
    Next shp

    ' Also clean up the old button on the wrong sheet
    On Error Resume Next
    Dim wsOld As Worksheet
    Set wsOld = ThisWorkbook.Sheets("Executive Summary")
    If Not wsOld Is Nothing Then
        For Each shp In wsOld.Shapes
            If shp.Name = "btnExportJSON" Then shp.Delete
        Next shp
    End If
    On Error GoTo BtnErr

    ' Create button in cell M2 area (top-right, out of the way)
    Dim btn As Shape
    Set btn = ws.Shapes.AddShape(msoShapeRoundedRectangle, _
        ws.Range("M2").Left, ws.Range("M2").Top, 130, 32)

    With btn
        .Name = "btnExportJSON"
        .TextFrame2.TextRange.Text = "Export data.json"
        .TextFrame2.TextRange.Font.Size = 11
        .TextFrame2.TextRange.Font.Bold = msoTrue
        .TextFrame2.TextRange.Font.Fill.ForeColor.RGB = RGB(255, 255, 255)
        .TextFrame2.TextRange.ParagraphFormat.Alignment = msoAlignCenter
        .Fill.ForeColor.RGB = RGB(152, 30, 50)  ' WSU Crimson
        .Line.Visible = msoFalse
        .OnAction = "ExportDataJSON.ExportDataJSON"
    End With

    MsgBox "Export button added to 'Executive Summary (Print)' sheet!" & vbCrLf & vbCrLf & _
           "Click the crimson 'Export data.json' button anytime to update the web app data.", _
           vbInformation, "Button Created"
    Exit Sub

BtnErr:
    MsgBox "Could not create button: " & Err.Description, vbExclamation
End Sub
