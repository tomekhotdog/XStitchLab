 # XStitchLab Technical Pipeline - Project Plan         
                                                         
  ## Overview                                            
  Build a local Python toolchain for end-to-end          
  cross-stitch pattern generation:                       
  **Image idea → AI generation → Pixelation → Color      
  mapping → Pattern output → Visualization → Thread      
  estimation**                                           
                                                         
  ## Technical Decisions                                 
  - **Package manager**: uv (fast, modern Python         
  management)                                            
  - **AI generation**: OpenAI DALL-E API                 
  - **Output formats**: PDF (printable patterns) +       
  PNG (previews)                                         
  - **Interface**: CLI core + Streamlit GUI for          
  pipeline visualization                                 
                                                         
  ---                                                    
                                                         
  ## Pipeline Components                                 
                                                         
  ### 1. Image Input/Generation                          
  - Accept local image files (PNG, JPG)                  
  - AI image generation via OpenAI DALL-E 3              
  - Prompt templates optimized for                       
  cross-stitch-friendly output (simple shapes, clear     
  outlines, limited colors)                              
                                                         
  ### 2. Image Processing                                
  - Resize to target grid (e.g., 40×40, 60×60,           
  80×80)                                                 
  - Color quantization (reduce to N colors)              
  - Optional: edge enhancement, background removal       
  - Dithering options (on/off) for gradient handling     
                                                         
  ### 3. Thread Color Mapping                            
  - Map quantized colors to real thread palette (DMC     
  standard - ~500 colors)                                
  - DMC color database with RGB values, codes, names     
  - **Difficulty control**: limit palette size           
  (fewer colors = easier project)                        
  - Color distance algorithms (CIELAB ΔE for             
  perceptual accuracy)                                   
  - "Substitute similar" feature to reduce thread        
  count                                                  
                                                         
  ### 4. Pattern Generation                              
  - Symbol grid (unique symbol per thread color)         
  - Thread legend with DMC codes, names, symbols         
  - Stitch counts per color                              
  - Grid lines every 10 stitches (standard practice)     
  - Metadata: dimensions, fabric size                    
  recommendations, difficulty rating                     
                                                         
  ### 5. Thread Estimation                               
  - Count stitches per color                             
  - Calculate thread length based on:                    
  - Fabric count (14ct, 16ct, 18ct)                      
  - Stitch type (full cross, half, backstitch)           
  - Wastage factor (~20%)                                
  - Output: skeins/meters needed per DMC color           
                                                         
  ### 6. Visualization & Output                          
  - **Preview modes**:                                   
  - Symbolic grid (for stitching)                        
  - Color block preview (how it will look)               
  - Thread-realistic render                              
  - **Export formats**: PDF (printable), PNG, JSON       
  (data)                                                 
                                                         
  ---                                                    
                                                         
  ## Technical Architecture                              
                                                         
  ```                                                    
  xstitchlab/                                            
  ├── cli.py                    # CLI entry point        
  (typer)                                                
  ├── app.py                    # Streamlit GUI          
  ├── core/                                              
  │   ├── __init__.py                                    
  │   ├── image_input.py        # Load/validate          
  images                                                 
  │   ├── ai_generator.py       # OpenAI DALL-E          
  integration                                            
  │   ├── pixelator.py          # Resize + quantize      
  │   ├── color_mapper.py       # RGB → DMC mapping      
  │   ├── pattern.py            # Pattern data           
  structure                                              
  │   ├── thread_calc.py        # Thread estimation      
  │   └── visualizer.py         # Render previews        
  ├── data/                                              
  │   └── dmc_colors.json       # DMC thread             
  database (~500 colors)                                 
  ├── export/                                            
  │   ├── pdf_exporter.py       # PDF pattern            
  generation                                             
  │   └── png_exporter.py       # Image export           
  ├── prompts/                                           
  │   └── templates.py          # DALL-E prompt          
  templates                                              
  ├── tests/                                             
  │   └── ...                                            
  └── pyproject.toml            # uv/project config      
  ```                                                    
                                                         
  **Key Dependencies:**                                  
  - `pillow` - image processing                          
  - `numpy` - color math, array ops                      
  - `scikit-learn` - k-means for color quantization      
  - `colormath` - CIELAB color distance (perceptual      
  accuracy)                                              
  - `openai` - DALL-E API                                
  - `fpdf2` - PDF generation (lighter than               
  reportlab)                                             
  - `typer` - CLI framework                              
  - `streamlit` - GUI for pipeline visualization         
                                                         
  ---                                                    
                                                         
  ## Phased Build Plan                                   
                                                         
  ### Phase 1: Foundation + Core Pipeline                
  - [ ] Project setup with uv (pyproject.toml,           
  structure, dependencies)                               
  - [ ] DMC color database (JSON: ~500 colors with       
  RGB, code, name)                                       
  - [ ] Image loading + validation                       
  - [ ] Basic pixelation (resize to grid)                
  - [ ] Color quantization (k-means to N colors)         
  - [ ] RGB → DMC mapping (nearest neighbor in RGB       
  space)                                                 
  - [ ] Pattern data structure (grid, legend,            
  metadata)                                              
  - [ ] PNG export (color grid + symbol grid)            
  - [ ] Basic CLI: `xstitch convert image.png --size     
  40 --colors 8`                                         
                                                         
  ### Phase 2: Color Accuracy + Controls                 
  - [ ] CIELAB color distance for perceptually           
  accurate DMC matching                                  
  - [ ] Difficulty control (max color count)             
  - [ ] "Merge similar" feature (reduce colors           
  post-quantization)                                     
  - [ ] Dithering on/off toggle                          
  - [ ] Edge enhancement preprocessing                   
  - [ ] Full pattern legend with symbols, DMC codes,     
  names                                                  
                                                         
  ### Phase 3: Thread Estimation                         
  - [ ] Stitch counting per color                        
  - [ ] Thread length formula (based on fabric           
  count)                                                 
  - [ ] Support for 14ct, 16ct, 18ct Aida                
  - [ ] Wastage factor (configurable, default ~20%)      
  - [ ] Skein/meter estimation per color                 
  - [ ] Shopping list export (text/JSON)                 
                                                         
  ### Phase 4: AI Image Generation                       
  - [ ] OpenAI API integration (DALL-E 3)                
  - [ ] Prompt templates by theme (Christmas, pets,      
  nature, etc.)                                          
  - [ ] Style modifiers for cross-stitch-friendly        
  output                                                 
  - [ ] CLI: `xstitch generate "cute robin on holly      
  branch" --style christmas`                             
  - [ ] Prompt refinement based on results               
                                                         
  ### Phase 5: PDF Export                                
  - [ ] Printable PDF pattern (symbol grid)              
  - [ ] Color key page                                   
  - [ ] Thread shopping list page                        
  - [ ] Pagination for larger patterns                   
  - [ ] Cover page with preview image                    
                                                         
  ### Phase 6: Streamlit GUI                             
  - [ ] Pipeline visualization (step-by-step             
  preview)                                               
  - [ ] Interactive controls (grid size, color           
  count, dithering)                                      
  - [ ] Side-by-side comparison (original →              
  pixelated → pattern)                                   
  - [ ] AI generation interface                          
  - [ ] One-click export (PDF + PNG)                     
  - [ ] Thread estimation display                        
                                                         
  ---                                                    
                                                         
  ## GUI Design (Streamlit)                              
                                                         
  The GUI will show the pipeline as a visual flow:       
                                                         
  ```                                                    
  ┌─────────────┐    ┌─────────────┐                     
  ┌─────────────┐    ┌─────────────┐                     
  │   INPUT     │ →  │  PIXELATE   │ →  │  MAP           
  COLORS │ →  │   OUTPUT    │                            
  │             │    │             │    │                
  │    │             │                                   
  │ Upload or   │    │ Grid size   │    │ DMC            
  palette │    │ PDF + PNG   │                           
  │ Generate    │    │ + quantize  │    │ + controls     
  │    │ + shopping  │                                   
  └─────────────┘    └─────────────┘                     
  └─────────────┘    └─────────────┘                     
  ```                                                    
                                                         
  Each stage shows:                                      
  - Preview image at that step                           
  - Controls relevant to that stage                      
  - Ability to adjust and re-run                         
                                                         
  ---                                                    
                                                         
  ## Thread Brand Note                                   
  Using **DMC** as the standard thread palette for       
  MVP:                                                   
  - Industry standard, widely available globally         
  - Well-documented RGB values exist                     
  - Can add Anchor/others later via palette plugins      
                                                         
  ---                                                    
                                                         
  ## Verification Strategy                               
                                                         
  **Unit Tests:**                                        
  - Color distance calculations (RGB, CIELAB)            
  - DMC nearest-neighbor matching (known inputs →        
  expected outputs)                                      
  - Thread length calculations                           
  - Grid dimension math                                  
                                                         
  **Integration Tests:**                                 
  - End-to-end: test image → pattern JSON → PNG →        
  PDF                                                    
  - Color quantization consistency                       
                                                         
  **Manual QA:**                                         
  - Generate sample Christmas designs                    
  - Print PDF patterns, verify readability               
  - Cross-check thread estimates against known           
  patterns                                               
  - Validate GUI workflow end-to-end                     
                                                         
  **Test Command:**                                      
  ```bash                                                
  uv run pytest tests/                                   
  uv run streamlit run app.py  # Manual GUI testing      
  ```                                                    
                                                         
  ---                                                    
                                                         
  ## Files to Create (in order)                          
                                                         
  1. `pyproject.toml` - project config +                 
  dependencies                                           
  2. `data/dmc_colors.json` - thread color database      
  3. `core/pattern.py` - data structures                 
  4. `core/image_input.py` - image loading               
  5. `core/pixelator.py` - resize + quantize             
  6. `core/color_mapper.py` - RGB → DMC                  
  7. `core/visualizer.py` - render previews              
  8. `export/png_exporter.py` - PNG output               
  9. `cli.py` - CLI interface                            
  10. `core/thread_calc.py` - thread estimation          
  11. `export/pdf_exporter.py` - PDF output              
  12. `core/ai_generator.py` - DALL-E integration        
  13. `prompts/templates.py` - prompt templates          
  14. `app.py` - Streamlit GUI 