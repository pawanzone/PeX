$ErrorActionPreference = "Stop"

$workspaceRoot = "C:\Users\pawan\.gemini\antigravity\scratch\pex_platform"
$pptxPath = Join-Path $workspaceRoot "docs\PEX_CXO_FIVE_PAGE_EXECUTIVE_ARCHITECTURE.pptx"
$pdfPath = Join-Path $workspaceRoot "docs\PEX_CXO_FIVE_PAGE_EXECUTIVE_ARCHITECTURE.pdf"
$cxoPagesDir = Join-Path $workspaceRoot "docs\cxo_pages"

if (-not (Test-Path $cxoPagesDir)) {
    New-Item -ItemType Directory -Path $cxoPagesDir -Force | Out-Null
}

$pageNames = @(
    "01_why_banks_need_pex",
    "02_what_is_pex",
    "03_how_pex_resolves",
    "04_how_pex_fits",
    "05_why_trust_and_scale"
)

Write-Host "Starting PowerPoint COM..."
$ppt = New-Object -ComObject PowerPoint.Application

try {
    Write-Host "Opening PPTX: $pptxPath"
    $pres = $ppt.Presentations.Open($pptxPath, [Microsoft.Office.Core.MsoTriState]::msoTrue, [Microsoft.Office.Core.MsoTriState]::msoFalse, [Microsoft.Office.Core.MsoTriState]::msoFalse)
    
    Write-Host "Exporting full presentation to PDF: $pdfPath"
    # 32 is ppSaveAsPDF
    $pres.SaveAs($pdfPath, 32)
    Write-Host "Full PDF exported successfully!"

    # Export slide images and individual one-pagers
    for ($i = 1; $i -le $pres.Slides.Count; $i++) {
        $slide = $pres.Slides.Item($i)
        $pageName = $pageNames[$i - 1]
        
        # Export high-res PNG image
        $pngPath = Join-Path $cxoPagesDir "$pageName.png"
        $slide.Export($pngPath, "PNG", 1920, 1080)
        Write-Host "Exported PNG slide $i to $pngPath"
    }

    $pres.Close()
    Write-Host "Presentation closed."

    # Generate individual 1-page PDFs from individual slides
    for ($i = 1; $i -le $pageNames.Length; $i++) {
        $pageName = $pageNames[$i - 1]
        $singlePres = $ppt.Presentations.Add([Microsoft.Office.Core.MsoTriState]::msoFalse)
        $singlePres.PageSetup.SlideWidth = 13.333 * 72
        $singlePres.PageSetup.SlideHeight = 7.5 * 72

        # Insert specific slide
        $singlePres.Slides.InsertFromFile($pptxPath, 0, $i, $i)
        $singlePdfPath = Join-Path $cxoPagesDir "$pageName.pdf"
        $singlePres.SaveAs($singlePdfPath, 32)
        $singlePres.Close()
        Write-Host "Exported single-page PDF $i to $singlePdfPath"
    }

} finally {
    $ppt.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}

Write-Host "All exports completed successfully!"
