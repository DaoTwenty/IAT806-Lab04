# Lab 04 — The Dance Floor

In class we made a grid of dancers with two nested loops. Every cell has its own color and speed, stored in 2D arrays. `animate()` draws one dancer.

In this lab the dancers **react to the mouse**, and the floor gets **two different dances**. Then you put it on your website.

## Start from the in-class sketch

Use your own code from class. If it isn't working, use the [`starter/`](starter/) folder:

```
starter/
├── sketch.js         the in-class sketch, ready for your website
├── dance_frames/     dance0.png ... dance7.png   (8 poses)
└── jump_frames/      jump0.png ... jump3.png     (4 poses, the second dance)
```

![The four jump poses](jump_preview.png)

1. In your website repo, copy your `lab-03/` folder and rename the copy `lab-04`.
2. On this repo's GitHub page, click the green **Code** button, then **Download ZIP**. Unzip it.
3. Copy `jump_frames/` into `lab-04/`. If you're using the starter, copy everything inside `starter/` and let it replace `sketch.js`.
4. Open `lab-04/index.html` with Live Server. You should see the grid before you change anything.

Better: use your own frames from Lab 03 for one of the dances.

## What to add

Do **both**.

### 1. Dancers that react to the mouse

Each dancer checks how far it is from the mouse and uses that distance as its speed. Close to the mouse: fast. Far away: slow. Or the other way around.

Use two p5 functions:

- `dist(x1, y1, x2, y2)` gives the distance between two points.
- `map(value, start1, stop1, start2, stop2)` moves a number from one range to another. `map(d, 0, 500, 2, 20)` turns a distance from 0 to 500 into a speed from 2 to 20.

Do it **inside the nested loop** in `draw()`, so each dancer gets its own distance.

<details>
<summary><b>Hint 1:</b> where is each dancer?</summary>

The dancer at column `i`, row `j` has its top-left corner at `i * colWidth, j * rowHeight`. Add half a cell to get the middle:

```js
let x = i * colWidth + colWidth / 2;
let y = j * rowHeight + rowHeight / 2;
let d = dist(x, y, mouseX, mouseY);
```

</details>

<details>
<summary><b>Hint 2:</b> what numbers go in <code>map()</code>?</summary>

The smallest distance is `0`. The biggest is corner to corner:

```js
let maxDist = dist(0, 0, width, height);
```

Look at `getFrameIndex()`: `speed` is how many frames each pose stays on screen. **Small = fast. Big = slow.**

```js
let speed = map(d, 0, maxDist, 2, 20);
```

Pass `speed` to `animate()` instead of `speeds[i][j]`.

</details>

<details>
<summary><b>Hint 3:</b> now they all dance in sync. Where did the random speeds go?</summary>

Keep the random speed and scale it with the distance:

```js
let speed = speeds[i][j] * map(d, 0, maxDist, 0.5, 3);
```

Never let the speed hit `0`.

</details>

### 2. Two dances on one floor

Alternate the grid between **two animations**: the 8 dance poses and the 4 jump poses (or your own). Checkerboard, stripes, your call. Both dances have to be on the floor.

Use **one** `animate()` function and pass it a different array. Don't copy the function.

<details>
<summary><b>Hint 4:</b> loading the second dance</summary>

`frames2` is already at the top of the sketch, empty. Fill it in `setup()` with a loop, like `frames`. There are **4** jump poses, not 8.

</details>

<details>
<summary><b>Hint 5:</b> which dance goes in which cell?</summary>

`n % 2` is `0` for even numbers and `1` for odd.

- `i % 2` alternates by column: stripes.
- `(i + j) % 2` alternates both ways: a checkerboard. Try it on paper.

Pick the array, then call `animate()` once:

```js
let danceFrames;
if ((i + j) % 2 === 0) {
  danceFrames = frames;
} else {
  danceFrames = frames2;
}
animate(danceFrames, speed, ...);
```

</details>

<details>
<summary><b>Hint 6:</b> everything freezes after a moment</summary>

Check the console for `Cannot read properties of undefined (reading 'width')`. Then look at this line in `getFrameIndex()`:

```js
let index = slowFrame % frames.length;
```

Which `frames` is that? Inside `animate()`, `frames` is the parameter you passed in. `getFrameIndex()` doesn't have that parameter, so it uses the **global** `frames`, which has 8 poses. It returns indexes up to 7, but `frames2` only has 4.

Fix: give `getFrameIndex()` a parameter for the array, and pass it from `animate()`:

```js
let index = getFrameIndex(frames, speed);
```

</details>

### Bonus

- Use the distance for **more than speed**: size (see the TODO in `animate()`), `fill()` alpha, or `tint()`.
- Use the distance to **pick the dance**: jump near the mouse, dance far away.
- Add a **third** dance.

Weird is good. Have fun with it.

Put a **comment** above each thing you add that says what it does, in your own words.

## How to hand it in

1. Edit `lab-04/index.html`: change the title and the `<h1>` to Lab 04, and write a sentence or two about how to play with it.
2. Add a link to it on `projects/iat-806/index.html`.
3. Commit and sync, then check that it works at:

```
https://your-username.github.io/projects/iat-806/lab-04/
```

In **Canvas**, submit:

1. The link to your live sketch.
2. The link to your `lab-04` folder in your GitHub repo.

Need a reminder on adding a folder to your site? See [section 4 of the personal-website README](https://github.com/IAT-806/personal-website#4-add-a-submission).

## If something doesn't work

Open the browser console (right-click the page → **Inspect** → **Console**) and read the red text.

- **Blank canvas and `404 (File not found)`**: an image path is wrong. Check the folder name, the file name, and the extension.
- **Everything freezes, and the console says `Cannot read properties of undefined (reading 'width')`**: an index is past the end of an array. See Hint 6.
- **Dancers flicker like crazy or barely move**: your speed is too small, negative, or huge. Put `console.log(speed)` in the loop and check the numbers.
- **Works with Live Server but not on GitHub Pages**: check capital letters. GitHub Pages cares about `Jump0.png` vs `jump0.png`.
