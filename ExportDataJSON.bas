Attribute VB_Name = "ExportDataJSON"
Option Explicit

' =====================================================================
' ExportDataJSON - Exports Executive Summary, HDD, and Kintec data
' to data.json for the Energy Cost Projection Web App
'
' Usage: Click the "Export Data" button on the Executive Summary sheet,
'        or run ExportDataJSON from the Macros menu.
' =====================================================================

Public Sub ExportDataJSON()
    On Error GoTo ErrHandler

    Dim ws As Worksheet
    Dim json As String
    Dim filePath As String
    Dim fNum As Integer
    Dim i As Long

    Application.StatusBar = "Exporting data.json..."

    ' Build the JSON string
    json = "{" & vbCrLf

    ' --- Last Updated ---
    json = json & "  ""lastUpdated"": """ & Format(Now, "mmmm d, yyyy") & """," & vbCrLf

    ' =================================================================
    ' FY2026 ACTUALS / FORECASTS  (Executive Summary rows 4-15)
    ' =================================================================
    Set ws = ThisWorkbook.Sheets("Executive Summary")

    json = json & "  ""fy26"": {" & vbCrLf
    json = json & "    ""totalActual"": [" & ReadRow(ws, 4, 15, 2) & "]," & vbCrLf
    json = json & "    ""elecActual"": [" & ReadRow(ws, 4, 15, 3) & "]," & vbCrLf
    json = json & "    ""gasActual"": [" & ReadRow(ws, 4, 15, 4) & "]," & vbCrLf
    json = json & "    ""totalFcast"": [" & ReadRow(ws, 4, 15, 5) & "]," & vbCrLf
    json = json & "    ""elecFcast"": [" & ReadRow(ws, 4, 15, 6) & "]," & vbCrLf
    json = json & "    ""gasFcast"": [" & ReadRow(ws, 4, 15, 7) & "]," & vbCrLf
    json = json & "    ""kintecFcast"": [" & ReadRow(ws, 4, 15, 8) & "]," & vbCrLf
    json = json & "    ""avistaFcast"": [" & ReadRow(ws, 4, 15, 9) & "]," & vbCrLf
    json = json & "    ""hedge"": " & Format(ws.Cells(4, 11).Value * 100, "0.0") & vbCrLf
    json = json & "  }," & vbCrLf

    ' =================================================================
    ' FY2025 GAS  (Executive Summary rows 21-32)
    ' =================================================================
    json = json & "  ""fy25gas"": {" & vbCrLf
    json = json & "    ""cost"": [" & ReadRow(ws, 21, 32, 2) & "]," & vbCrLf
    json = json & "    ""mmbtu"": [" & ReadRow(ws, 21, 32, 3) & "]," & vbCrLf
    json = json & "    ""perUnit"": [" & ReadRowDec(ws, 21, 32, 4, 2) & "]," & vbCrLf
    json = json & "    ""kintec"": [" & ReadRow(ws, 21, 32, 8) & "]," & vbCrLf
    json = json & "    ""avista"": [" & ReadRow(ws, 21, 32, 9) & "]" & vbCrLf
    json = json & "  }," & vbCrLf

    ' =================================================================
    ' FY2026 ENERGY USE  (Executive Summary rows 37-48)
    ' =================================================================
    json = json & "  ""energyUse"": {" & vbCrLf
    json = json & "    ""totalActual"": [" & ReadRow(ws, 37, 48, 2) & "]," & vbCrLf
    json = json & "    ""elecActual"": [" & ReadRow(ws, 37, 48, 3) & "]," & vbCrLf
    json = json & "    ""gasActual"": [" & ReadRow(ws, 37, 48, 4) & "]," & vbCrLf
    json = json & "    ""totalFcast"": [" & ReadRow(ws, 37, 48, 5) & "]," & vbCrLf
    json = json & "    ""kwhActual"": [" & ReadRow(ws, 37, 48, 8) & "]," & vbCrLf
    json = json & "    ""kwhRate"": [" & ReadRowDec(ws, 37, 48, 10, 4) & "]" & vbCrLf
    json = json & "  }," & vbCrLf

    ' =================================================================
    ' YEAR-OVER-YEAR MMBTU  (Executive Summary rows 53-64)
    ' =================================================================
    json = json & "  ""yoy"": {" & vbCrLf
    json = json & "    ""fy24total"": [" & ReadRow(ws, 53, 64, 2) & "]," & vbCrLf
    json = json & "    ""fy24elec"": [" & ReadRow(ws, 53, 64, 3) & "]," & vbCrLf
    json = json & "    ""fy24gas"": [" & ReadRow(ws, 53, 64, 4) & "]," & vbCrLf
    json = json & "    ""fy25total"": [" & ReadRow(ws, 53, 64, 5) & "]," & vbCrLf
    json = json & "    ""fy25elec"": [" & ReadRow(ws, 53, 64, 6) & "]," & vbCrLf
    json = json & "    ""fy25gas"": [" & ReadRow(ws, 53, 64, 7) & "]," & vbCrLf
    json = json & "    ""fy26total"": [" & ReadRow(ws, 53, 64, 8) & "]," & vbCrLf
    json = json & "    ""fy26elec"": [" & ReadRow(ws, 53, 64, 9) & "]," & vbCrLf
    json = json & "    ""fy26gas"": [" & ReadRow(ws, 53, 64, 10) & "]" & vbCrLf
    json = json & "  }," & vbCrLf

    ' =================================================================
    ' CUMULATIVE SUMMARY  (Executive Summary rows 69-80)
    ' =================================================================
    json = json & "  ""cumul"": {" & vbCrLf
    json = json & "    ""actual"": [" & ReadRow(ws, 69, 80, 2) & "]," & vbCrLf
    json = json & "    ""forecast"": [" & ReadRow(ws, 69, 80, 3) & "]," & vbCrLf
    json = json & "    ""delta"": [" & ReadRow(ws, 69, 80, 4) & "]," & vbCrLf
    json = json & "    ""deltaPct"": [" & ReadRowDec(ws, 69, 80, 5, 1) & "]," & vbCrLf
    json = json & "    ""mmbtuAct"": [" & ReadRow(ws, 69, 80, 6) & "]," & vbCrLf
    json = json & "    ""elecRate"": [" & ReadRowDec(ws, 69, 80, 8, 2) & "]," & vbCrLf
    json = json & "    ""gasRate"": [" & ReadRowDec(ws, 69, 80, 10, 2) & "]" & vbCrLf
    json = json & "  }," & vbCrLf

    ' =================================================================
    ' HDD DATA  (HDD Data sheet rows 7-18, cols C-E)
    ' =================================================================
    Set ws = ThisWorkbook.Sheets("HDD Data")

    json = json & "  ""hdd"": {" & vbCrLf
    json = json & "    ""fy25"": [" & ReadRow(ws, 7, 18, 3) & "]," & vbCrLf
    json = json & "    ""fy26"": [" & ReadRow(ws, 7, 18, 4) & "]," & vbCrLf
    json = json & "    ""normal"": [" & ReadRow(ws, 7, 18, 5) & "]" & vbCrLf
    json = json & "  }," & vbCrLf

    ' =================================================================
    ' KINTEC DATA  (Kintec Data sheet, variable rows)
    ' =================================================================
    Set ws = ThisWorkbook.Sheets("Kintec Data")

    ' Find last row with data in column A
    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    Dim monthsStr As String, dthsStr As String, costStr As String
    monthsStr = ""
    dthsStr = ""
    costStr = ""

    For i = 2 To lastRow
        If ws.Cells(i, 1).Value <> "" Then
            Dim dt As Date
            dt = ws.Cells(i, 1).Value
            Dim monLabel As String
            monLabel = Format(dt, "mmm") & "-" & Format(dt, "yy")

            If i > 2 Then
                monthsStr = monthsStr & ","
                dthsStr = dthsStr & ","
                costStr = costStr & ","
            End If

            monthsStr = monthsStr & """" & monLabel & """"
            dthsStr = dthsStr & CLng(ws.Cells(i, 6).Value)
            costStr = costStr & CLng(ws.Cells(i, 5).Value)
        End If
    Next i

    json = json & "  ""kintec"": {" & vbCrLf
    json = json & "    ""months"": [" & monthsStr & "]," & vbCrLf
    json = json & "    ""dths"": [" & dthsStr & "]," & vbCrLf
    json = json & "    ""cost"": [" & costStr & "]" & vbCrLf
    json = json & "  }" & vbCrLf

    json = json & "}"

    ' Write the file
    filePath = ThisWorkbook.Path & "\data.json"
    fNum = FreeFile
    Open filePath For Output As #fNum
    Print #fNum, json
    Close #fNum

    Application.StatusBar = False
    MsgBox "Export complete!" & vbCrLf & vbCrLf & _
           "data.json saved to:" & vbCrLf & filePath & vbCrLf & vbCrLf & _
           "Upload this file to your GitHub repo to update the web app.", _
           vbInformation, "Energy Web App Export"
    Exit Sub

ErrHandler:
    Application.StatusBar = False
    MsgBox "Export failed:" & vbCrLf & vbCrLf & Err.Description, _
           vbCritical, "Export Error"
End Sub

' -----------------------------------------------------------------
' Helper: Read a column across rows, return comma-separated integers
' -----------------------------------------------------------------
Private Function ReadRow(ws As Worksheet, startRow As Long, endRow As Long, col As Long) As String
    Dim result As String
    Dim r As Long
    result = ""
    For r = startRow To endRow
        If r > startRow Then result = result & ","
        result = result & CLng(ws.Cells(r, col).Value)
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
    fmt = "0." & String(decimals, "0")
    result = ""
    For r = startRow To endRow
        If r > startRow Then result = result & ","
        Dim v As Variant
        v = ws.Cells(r, col).Value
        ' Handle percentage values stored as decimals (e.g. 0.087 -> 8.7)
        If col = 5 And v <> 0 And Abs(v) < 1 Then
            v = v * 100
        End If
        result = result & Format(v, fmt)
    Next r
    ReadRowDec = result
End Function

' =====================================================================
' AddExportButton - Run ONCE to add a clickable button to the sheet
' =====================================================================
Public Sub AddExportButton()
    On Error GoTo BtnErr

    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets("Executive Summary")

    ' Delete existing button if present
    Dim shp As Shape
    For Each shp In ws.Shapes
        If shp.Name = "btnExportJSON" Then shp.Delete
    Next shp

    ' Create button in cell N3 area (top-right, out of the way)
    Dim btn As Shape
    Set btn = ws.Shapes.AddShape(msoShapeRoundedRectangle, _
        ws.Range("M2").Left, ws.Range("M2").Top, 120, 32)

    With btn
        .Name = "btnExportJSON"
        .TextFrame2.TextRange.Text = "Export Data"
        .TextFrame2.TextRange.Font.Size = 11
        .TextFrame2.TextRange.Font.Bold = msoTrue
        .TextFrame2.TextRange.Font.Fill.ForeColor.RGB = RGB(255, 255, 255)
        .TextFrame2.TextRange.ParagraphFormat.Alignment = msoAlignCenter
        .Fill.ForeColor.RGB = RGB(152, 30, 50)  ' WSU Crimson
        .Line.Visible = msoFalse
        .OnAction = "ExportDataJSON"
    End With

    MsgBox "Export button added to the Executive Summary sheet!" & vbCrLf & vbCrLf & _
           "Click the crimson 'Export Data' button anytime to update data.json.", _
           vbInformation, "Button Created"
    Exit Sub

BtnErr:
    MsgBox "Could not create button: " & Err.Description, vbExclamation
End Sub
