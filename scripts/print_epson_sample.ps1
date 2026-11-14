# Print Tax Invoice directly to Epson EcoTank L6460 / Inkjet / Document Printer
param(
    [string]$PrinterName = "L6460 Series(Network)",
    [string]$Format = "A4",
    [string]$JsonPath = ""
)

Add-Type -AssemblyName System.Drawing

$doc = New-Object System.Drawing.Printing.PrintDocument
$doc.PrinterSettings.PrinterName = $PrinterName

if (-not $doc.PrinterSettings.IsValid) {
    Write-Error "Printer '$PrinterName' is not valid or not found."
    exit 1
}

$isA5 = ($Format -eq "A5")
if ($isA5) {
    foreach ($ps in $doc.PrinterSettings.PaperSizes) {
        if ($ps.PaperName -match "A5") {
            $doc.DefaultPageSettings.PaperSize = $ps
            break
        }
    }
} else {
    foreach ($ps in $doc.PrinterSettings.PaperSizes) {
        if ($ps.PaperName -match "A4") {
            $doc.DefaultPageSettings.PaperSize = $ps
            break
        }
    }
}

# Load invoice data (either from JSON file or default sample)
$storeName = "MOIRA LUXE"
$storeAddress = "Main Road, Thuckalay, Kanyakumari Dist - 629175"
$storePhone = "8438353504"
$storeEmail = "moiraluxe@gmail.com"
$storeGst = "33AAAAA0000A1Z5"
$invoiceNo = "ML-SAMPLE-2026"
$customerName = "Priyadharshini M"
$customerPhone = "+91 98765 43210"
$customerPlace = "Thuckalay"
$paymentMethod = "CASH / UPI"
$cashier = "Ajay"
$nowStr = (Get-Date).ToString("dd-MM-yyyy  hh:mm tt")

$items = @(
    @{ idx=1; name="22K Gold Plated Choker Necklace"; code="JW-CH-01"; qty=1; rate=3499.00; disc=200.00; amt=3299.00 },
    @{ idx=2; name="Kundan Pearl Drop Earrings (Pair)"; code="JW-ER-08"; qty=2; rate=1250.00; disc=100.00; amt=2400.00 },
    @{ idx=3; name="Diamond Cut Silver Plated Bangle"; code="JW-BG-14"; qty=1; rate=1899.00; disc=50.00; amt=1849.00 }
)
$subtotal = 6648.00
$discount = 350.00
$tax = 189.00
$total = 6487.00
$words = "Six Thousand Four Hundred Eighty Seven Rupees Only"

if ($JsonPath -and (Test-Path $JsonPath)) {
    try {
        $raw = Get-Content $JsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($raw.store_name) { $storeName = $raw.store_name }
        if ($raw.store_address) { $storeAddress = $raw.store_address }
        if ($raw.store_phone) { $storePhone = $raw.store_phone }
        if ($raw.invoice_no) { $invoiceNo = $raw.invoice_no }
        if ($raw.customer_name) { $customerName = $raw.customer_name }
        if ($raw.customer_phone) { $customerPhone = $raw.customer_phone }
        if ($raw.customer_place) { $customerPlace = $raw.customer_place }
        if ($raw.payment_method) { $paymentMethod = $raw.payment_method.ToUpper() }
        if ($raw.cashier) { $cashier = $raw.cashier }
        if ($raw.created_at) { $nowStr = $raw.created_at }
        if ($raw.subtotal) { $subtotal = [double]$raw.subtotal }
        if ($raw.discount) { $discount = [double]$raw.discount }
        if ($raw.tax) { $tax = [double]$raw.tax }
        if ($raw.total) { $total = [double]$raw.total }
        if ($raw.words) { $words = $raw.words }

        if ($raw.items -and $raw.items.Count -gt 0) {
            $parsedItems = @()
            $i = 1
            foreach ($it in $raw.items) {
                $pName = if ($it.name) { $it.name } else { "Item" }
                $pCode = if ($it.code) { $it.code } else { ("SKU-{0:D3}" -f $i) }
                $pQty = if ($it.quantity) { [int]$it.quantity } else { 1 }
                $pRate = if ($it.price) { [double]$it.price } else { 0.0 }
                $pDisc = if ($it.discount) { [double]$it.discount } else { 0.0 }
                $pAmt = if ($it.amount) { [double]$it.amount } else { ($pQty * $pRate - $pDisc) }
                $parsedItems += @{ idx=$i; name=$pName; code=$pCode; qty=$pQty; rate=$pRate; disc=$pDisc; amt=$pAmt }
                $i++
            }
            $items = $parsedItems
        }
    } catch {
        Write-Warning "Failed to parse $JsonPath, falling back to default sample."
    }
}

$doc.DocumentName = "Tax Invoice - $invoiceNo"

$doc.add_PrintPage({
    param($sender, $e)
    $g = $e.Graphics
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit

    # Colors & Pens
    $brushDark = [System.Drawing.Brushes]::Black
    $brushSlate = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(71, 85, 105))
    $brushMuted = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(100, 116, 139))
    $penBorder = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(203, 213, 225), 1)
    $penDark = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(15, 23, 42), 2)
    $brushHeaderBg = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(241, 245, 249))
    $brushCardBg = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(248, 250, 252))

    # Fonts
    $fontTitle = New-Object System.Drawing.Font("Segoe UI", 20, [System.Drawing.FontStyle]::Bold)
    $fontBadge = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
    $fontBold = New-Object System.Drawing.Font("Segoe UI", 9.5, [System.Drawing.FontStyle]::Bold)
    $fontText = New-Object System.Drawing.Font("Segoe UI", 9.5, [System.Drawing.FontStyle]::Regular)
    $fontSmall = New-Object System.Drawing.Font("Segoe UI", 8.5, [System.Drawing.FontStyle]::Regular)
    $fontTotal = New-Object System.Drawing.Font("Segoe UI", 12, [System.Drawing.FontStyle]::Bold)

    $left = 40
    $top = 40
    $width = if ($isA5) { 720 } else { 740 }
    $right = $left + $width

    # Header
    $g.DrawString($storeName, $fontTitle, $brushDark, $left, $top)
    $badgeText = "TAX INVOICE"
    $badgeSize = $g.MeasureString($badgeText, $fontBadge)
    $badgeRect = New-Object System.Drawing.RectangleF(($right - $badgeSize.Width - 20), ($top + 5), ($badgeSize.Width + 20), ($badgeSize.Height + 8))
    $g.FillRectangle((New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(15, 23, 42))), $badgeRect)
    $g.DrawString($badgeText, $fontBadge, [System.Drawing.Brushes]::White, ($right - $badgeSize.Width - 10), ($top + 9))

    $y = $top + 38
    $g.DrawString("Luxury Jewellery & Lifestyle Fashion Accessories", $fontSmall, $brushSlate, $left, $y)
    $y += 16
    $g.DrawString("$storeAddress | Phone: $storePhone", $fontSmall, $brushSlate, $left, $y)
    $y += 16
    $g.DrawString("GSTIN: $storeGst | Email: $storeEmail", $fontSmall, $brushSlate, $left, $y)
    $y += 24

    # Meta Grid
    $cardHeight = 75
    $cardRect = New-Object System.Drawing.RectangleF($left, $y, $width, $cardHeight)
    $g.FillRectangle($brushCardBg, $cardRect)
    $g.DrawRectangle($penBorder, $left, $y, $width, $cardHeight)
    $g.DrawLine($penBorder, ($left + ($width / 2)), $y, ($left + ($width / 2)), ($y + $cardHeight))

    $g.DrawString("INVOICE DETAILS", $fontSmall, $brushMuted, ($left + 12), ($y + 8))
    $g.DrawString("Invoice No: $invoiceNo", $fontBold, $brushDark, ($left + 12), ($y + 24))
    $g.DrawString("Date: $nowStr", $fontText, $brushDark, ($left + 12), ($y + 40))
    $g.DrawString("Payment: $paymentMethod  |  Cashier: $cashier", $fontSmall, $brushSlate, ($left + 12), ($y + 56))

    $mid = $left + ($width / 2) + 12
    $g.DrawString("BILLED TO (CUSTOMER)", $fontSmall, $brushMuted, $mid, ($y + 8))
    $g.DrawString($customerName, $fontBold, $brushDark, $mid, ($y + 24))
    $g.DrawString("Phone: $customerPhone", $fontText, $brushDark, $mid, ($y + 40))
    $g.DrawString("Place: $customerPlace", $fontSmall, $brushSlate, $mid, ($y + 56))
    $y += $cardHeight + 16

    # Table Header
    $tblH = 26
    $g.FillRectangle($brushHeaderBg, $left, $y, $width, $tblH)
    $g.DrawRectangle($penBorder, $left, $y, $width, $tblH)

    $col1 = $left + 10
    $col2 = $left + 45
    $col3 = $left + 400
    $col4 = $left + 470
    $col5 = $left + 570
    $col6 = $left + 650

    $g.DrawString("#", $fontBold, $brushDark, $col1, ($y + 5))
    $g.DrawString("ITEM DESCRIPTION", $fontBold, $brushDark, $col2, ($y + 5))
    $g.DrawString("QTY", $fontBold, $brushDark, $col3, ($y + 5))
    $g.DrawString("RATE (Rs.)", $fontBold, $brushDark, $col4, ($y + 5))
    $g.DrawString("DISC (Rs.)", $fontBold, $brushDark, $col5, ($y + 5))
    $g.DrawString("AMOUNT (Rs.)", $fontBold, $brushDark, $col6, ($y + 5))
    $y += $tblH

    $totalQty = 0
    foreach ($item in $items) {
        $rowH = 34
        $totalQty += [int]$item.qty
        $g.DrawRectangle($penBorder, $left, $y, $width, $rowH)
        
        $g.DrawString($item.idx.ToString(), $fontText, $brushDark, ($col1 + 5), ($y + 6))
        $g.DrawString($item.name, $fontBold, $brushDark, $col2, ($y + 4))
        $g.DrawString("SKU: $($item.code)", $fontSmall, $brushMuted, $col2, ($y + 18))
        $g.DrawString($item.qty.ToString(), $fontBold, $brushDark, ($col3 + 8), ($y + 8))
        $g.DrawString(("{0:N2}" -f [double]$item.rate), $fontText, $brushDark, $col4, ($y + 8))
        $g.DrawString(("-{0:N2}" -f [double]$item.disc), $fontText, (New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(220, 38, 38))), $col5, ($y + 8))
        $g.DrawString(("{0:N2}" -f [double]$item.amt), $fontBold, $brushDark, $col6, ($y + 8))
        
        $y += $rowH
    }
    $y += 12

    # Totals
    $wordsW = 380
    $g.FillRectangle($brushCardBg, $left, $y, $wordsW, 70)
    $g.DrawRectangle($penBorder, $left, $y, $wordsW, 70)
    $g.DrawString("AMOUNT IN WORDS:", $fontSmall, $brushMuted, ($left + 10), ($y + 8))
    $g.DrawString($words, $fontBold, $brushDark, ($left + 10), ($y + 24))
    $g.DrawString("Total Items: $($items.Count)  |  Total Quantity: $totalQty", $fontSmall, $brushSlate, ($left + 10), ($y + 46))

    $totX = $left + 420
    $totValX = $right - 10
    $sfRight = New-Object System.Drawing.StringFormat
    $sfRight.Alignment = [System.Drawing.StringAlignment]::Far

    $ty = $y
    $g.DrawString("Subtotal:", $fontText, $brushSlate, $totX, $ty)
    $g.DrawString(("Rs. {0:N2}" -f $subtotal), $fontBold, $brushDark, $totValX, $ty, $sfRight)
    $ty += 20

    if ($discount -gt 0) {
        $g.DrawString("Total Discount:", $fontText, (New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(220, 38, 38))), $totX, $ty)
        $g.DrawString(("-Rs. {0:N2}" -f $discount), $fontBold, (New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(220, 38, 38))), $totValX, $ty, $sfRight)
        $ty += 20
    }

    if ($tax -gt 0) {
        $g.DrawString("GST (3%):", $fontText, $brushSlate, $totX, $ty)
        $g.DrawString(("+Rs. {0:N2}" -f $tax), $fontText, $brushSlate, $totValX, $ty, $sfRight)
        $ty += 20
    }

    $g.DrawLine($penDark, $totX, $ty, $right, $ty)
    $ty += 6
    $g.DrawString("TOTAL PAYABLE:", $fontTotal, $brushDark, $totX, $ty)
    $g.DrawString(("Rs. {0:N2}" -f $total), $fontTotal, (New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(15, 23, 42))), $totValX, $ty, $sfRight)
    $ty += 28
    $g.DrawLine($penDark, $totX, $ty, $right, $ty)
    $y = [Math]::Max(($y + 80), ($ty + 10))

    # Terms & Signature
    $y += 18
    $g.DrawLine((New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(203, 213, 225))), $left, $y, $right, $y)
    $y += 12

    $terms = "Terms & Conditions:`n1. Goods once sold can be exchanged within 7 days with original tax invoice.`n2. No cash refund on jewellery items.`n3. Thank you for shopping with $storeName!"
    $g.DrawString($terms, $fontSmall, $brushSlate, $left, $y)

    $signX = $right - 180
    $g.DrawLine($penDark, $signX, ($y + 35), ($signX + 160), ($y + 35))
    $g.DrawString("For $storeName", $fontBold, $brushDark, ($signX + 25), ($y + 40))
    $g.DrawString("Authorized Signatory", $fontSmall, $brushMuted, ($signX + 20), ($y + 55))

    $e.HasMorePages = $false
})

Write-Host "Sending Tax Invoice directly to printer: $PrinterName ($Format)..."
$doc.Print()
Write-Host "Print job sent successfully to $PrinterName!"
