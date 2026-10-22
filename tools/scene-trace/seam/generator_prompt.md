# Image-generator prompt: A → B transition band

## Inputs to attach

| File | Size | Use |
|---|---|---|
| `tools/scene-trace/seam/inpaint_canvas.png` | 937x1000 RGBA | Preferred (inpainting / generative fill). Rows 0–399 = A's bottom 400 rows; rows 400–619 transparent (repaint); rows 620–999 = B rows 220–599. |
| `tools/scene-trace/seam/inpaint_mask.png` | 937x1000 | White = repaint (rows 400–619). For tools that take a separate mask. |
| `tools/scene-trace/seam_ref.png` | 937x400 | A's bottom 400 rows, for tools that only take a reference image. |
| `tools/scene-trace/B_orig.png` | 937x1679 | B, for tools that need the full target as a second reference. |

## Prompt (inpainting tool, canvas + mask)

> Fill only the transparent band (rows 400–619) of this 937x1000 image. Keep every opaque pixel unchanged and keep the
> canvas exactly 937x1000. The image is one continuous top-down storybook forest scene in a soft pastel, painterly,
> hand-illustrated style: flat soft shading, fine leaf-cluster foliage, no outlines, no hard shadows. Paint the band so
> the scene reads as one unbroken illustration from the top edge of the band into the bottom edge of the band.
>
> Required continuity:
> - The cream dirt path enters the top of the band between x 385 and x 664 (279 px wide) and must leave the bottom of the
>   band between roughly x 424 and x 586, matching the path already there. Narrow it smoothly with soft, slightly
>   irregular edges and a few scattered round pebble stones the same colour as the ones above.
> - The brown earth bank on the right of the path (x 664–738 at the top of the band) must end inside the band in a natural
>   way: let it taper to nothing along the path edge or tuck under grass and leafy bushes. No brown bank reaches the
>   bottom edge of the band.
> - Left of the path (x 0–385): continue the bushes, grey boulder and flowers above into the large leafy tree canopy and
>   trunk below. Right of the path (x 738–937): continue the dark teal pine and grass above into the green bushes and grass
>   below.
> - Colours, brightness, and texture scale must match both neighbouring edges exactly; no new focal objects, no characters,
>   no text, no frame, no vignette, no change in lighting direction.

## Prompt (generator without inpainting, reference only)

> Using the attached image (937x400, the bottom of a top-down pastel storybook forest illustration) as the top edge,
> paint its downward continuation as a 937x620 image whose top 400 rows reproduce the reference exactly and whose bottom
> 220 rows lead into the attached second image's top (cream path narrowing from x 385–664 to about x 424–586, the right
> brown earth bank ending under grass and bushes, leafy tree canopy on the left, bushes and grass on the right). Same
> soft pastel painterly style, same texture scale, no new focal objects, no text.

## What happens with the result

The returned band replaces B's rows 0–219 (inpainting) or is cut in above B row 220 after alignment; a short
min-error cut (`seam/seam.py cut`, reduced to its Poisson pass) absorbs any residual colour offset at both ends, then the
numeric seam test and 1x/3x join crops are re-run before tracing.
