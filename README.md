# Coil Calculator

A calculator to determine the amount of stroke displacement (sag) on the
rear suspension of a mountain bike a particuler rider will produce with a
particule coil spring.

## The Math

The math to produce sag calculations is dead simple in the base case.

We can use:

- Rider weight and rear wheel bias to determine the "normalized" weight
- Stroke and wheel travel to generate a leverage ratio
- [Hooks law](https://en.wikipedia.org/wiki/Hooke%27s_law) to determine
the spring displacement based on the riders force

Assuming that the suspension platform has a linear leverage curve (more on
this later) you can represent the sag with algebra and solve it straight
forwardly.

This approach worked well for the first version of this tool, but in
trying to represent the reality of suspension design this becomes a larger
problem and moves us into non-linear suspension curves and calculus.

### Leverage Curves

As a mountain bike moves through the suspension, the force exerted on
the shock changes. Different suspension platforms have different curves,
and the leverage curves they create will have an affect on compression of
the spring.

Some platforms start with a high leverage ratio which reduces, others the
opposite, and others make 'U' or other shapes.

Here is an article I found that dives deeper into this.
[TODO: fully read to verifiy its good](https://vorsprungsuspension.com/blogs/learn/understanding-leverage-curves)

This means our once simple algebra equations now needs to incorporate this curve
data. Said in another way, our equation needs to account for difference forces
at different spring displacements.

#### What a Leverage Curve Represents

"Leverage" as these curves refer to it, is the change in wheel travel compared
to the change in shock stroke. These leverage curves typically use wheel travel
on the x axis, so that is the convention that I have stuck with in this calculator.

Think about what this line represents...

The curve *really* defines the position of the stroke in relation to the position of
the wheel travel. And based on the leverage at any given point, the end result
**must be that when the wheel moves fully through its travel, the shock moves
fully through its stroke... EXACTLY**. Not more, not less.

This should ring a bell! What these leverage curves really are, are reciprical
derivitives of wheel travel vs shock stroke!

Consider a typical derivitive graph you might have in math class.

```
x axis is x
y axis dy/dx (slope, rise over run, tangent... whatever you call it)
```

What we have is sooooo close to this.

```
x axis is wheel travel
y axis is wheel travel / shock stroke
```

In order to get to a traditional derivitive we need to flip that from "run
over rise" to "rise over run" and we can do that by taking the reciprical of
the leverage curve. At that point we'll then have a traditional derivitive.

```
x axis is wheel travel
y axis is shock stroke / wheel travel
```

Consider a bike with 160mm of wheel travel and a 60mm shock stroke. Whats the
area under this new (reciprical) leverage curve? 60mm!

**Taking the integral of the reciprical of the leverage curve from 0 to the 
end of the wheel travel MUST ALWAYS equal the shock stroke**. This fact should
help understand what these curves represent.


#### Selecting a Leverage Curve

We need a way for the user to be able to provide the calculator with one of
these leverage curves. There a a couple ways to do this: presets for different
bikes, different platforms, or maybe even allowing the user to draw the pivots
and calculate the leverage curve from that. I opted for something else.

The solution I went for is to provide 6 (for example) "handles" on a curve
that the user can drag up and down to match the curve of their bike.

I saw it the customization and accompanying math was going to be innevitable.
I can always add presets later.

**The resulting curve looks like a smooth curve but that is purely a cosmetic
desicion. In reality, we have 5 piecewise defined straight lines**

While you could use either a single or piecewise defined curve(s) to drive 
the underlying math, using piecewise defined linear equations make the math
much more approachable with negligable (non existant) real world difference
when all is said and done.

**So you can create any curve you want?**

No, you cannot. Remember, there is underlying math that defines what a valid
curve is.

If you adjust the curve you'll notice that every adjustment creates automatic
adjustments to every other part of the curve. The area under the reciprical of
this curve must never change, and that is what you see happen.

Ensuring this is the case is what dictates the set of curves that a user can
move through. It may seem infinetely adjustable, but its actually a finite set.


#### Applying the Curve

In order to insert the leverage curve into hooks law, we need to do a few
transformation to it. Right now its 5 piecewise defined lines, with leverage on
the y axis and wheel travel on the x axis. For hooks law, we need to know the
instantanious leverage at any give shock stroke... not wheel travel.

We can get to this through a series of transformations to each of our piecewise
defined lines.

1. Take the reciprical to get the d/dx of stroke to travel
2. Take the integral to get the mapping of stroke (y) to travel (x)
3. Take the inverse to the the mapping of travel (y) to stroke (x)
4. Take the derivitive to get the d/dx of travel to stroke  <-- THIS IS WHAT WE WANT

There may be an easier way to go from 1 to 4... but I couldn't reason about that.

At the end of all this you now have 5 piecewise defined functions that give
the leverage of on the shock at any given stroke... which inserted into hooks
law at each interval produce:

$$y = mx - my + ln(mX+b) - ln(\frac{kx}{wr})$$

As far as I know, this function is considered [transcendental](https://en.wikipedia.org/wiki/Transcendental_function)
because isolating the sag (x) is not possible. To solve, you have to use
analytical methods to zero in on the solution. I use
[newtons method](https://en.wikipedia.org/wiki/Newton%27s_method) in this case.

Evaluating this on each interval of our curve gives us our sag.
