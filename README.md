
[![Support me by buying on Gumroad !](https://user-images.githubusercontent.com/26815785/121318918-fceac680-c90b-11eb-8c52-e491bf54a57e.png)](https://gumroad.com/twinkelmann)


# Niche Loops

...also known as "Way too Niche and Peculiar but Actually Necessary Loop Tools", is an add-on that includes a few interesting loop tools.

A friend asked me to recreate a few nice features from 3dsmax in Blender, and so I did.

## Operators

As of now, this addon contains the following operators:

- Build End
- Build Corner
- Adjust Loops
- Adjust Adjacent Loops

### Build End

Builds a quad ending to two parallel loops based on the vertex or edge selection.

![niche-loops-build-end](https://user-images.githubusercontent.com/26815785/121320787-c4e48300-c90d-11eb-81ac-dd156a016aaa.gif)

### Build Corner

Builds a quad corner based on the vertex selection to make an edge-loop turn.

![niche-loops-build-corner](https://user-images.githubusercontent.com/26815785/121320620-9cf51f80-c90d-11eb-8156-727763fafe72.gif)

### Adjust Loops

Select two or more parallel edges and adjust the value to change the distance between them.

![niche_loops_adjust_loops](https://user-images.githubusercontent.com/26815785/121320442-7636e900-c90d-11eb-8333-0ec7ff072f3b.gif)

### Adjust Adjacent Loops

Select one or more edges and adjust the value to change the positions of the edges on either side of the selected loop.

![niche_loops_adjust_adjacent_loops](https://user-images.githubusercontent.com/26815785/121320291-4d165880-c90d-11eb-87ac-d9c82bc5e67d.gif)

## TODO

Here is a list of things I plan on adding in the future:

**Interactiveness**

For the two Adjust Loops operators, I want to implement a drag-to-adjust feature like you have when extruding or sliding an edge.

**Slide to the outside**

For the two Adjust Loops operators, I want to have a dropdown to choose betweenm sliding the points to the inside (current behavior), to the outside, or choosing automatically based on the sliding value.
It's an extra bit of complexity that wasn't in the reference tools, so I did not implement it in the first release.

## Contributing

Any contributions, bug fixes, or simply bug reports are well appreciated !
Feel free to create a issue on Github for feature requests too, but please keep them about the existing operators for now.

If you would like me to develop  an addon for you (paid work), feel free to get in touch by email twinkelmann(at)pm.me, or on Discord `twinkelmann#6921`
