from adapter import Solver, route_load
from adapters.starter import StarterSolver
from data import distance_matrix


SAFETY_S = 0.25


# =========================================================
# 1. 2-OPT
# =========================================================

def two_opt(d, route):

    if len(route) < 3:
        return False

    improved = False

    while True:

        changed = False
        n = len(route)

        for i in range(n - 1):

            a = route[i - 1] if i > 0 else 0

            for j in range(i + 1, n):

                b = route[j + 1] if j + 1 < n else 0

                old_cost = (
                    d[a][route[i]]
                    + d[route[j]][b]
                )

                new_cost = (
                    d[a][route[j]]
                    + d[route[i]][b]
                )

                if new_cost < old_cost:

                    route[i:j + 1] = reversed(
                        route[i:j + 1]
                    )

                    changed = True
                    improved = True
                    break

            if changed:
                break

        if not changed:
            break

    return improved


# =========================================================
# 2. IMPROVE ALL ROUTES
# =========================================================

def improve_routes(d, routes):

    changed = False

    for route in routes:

        if two_opt(d, route):
            changed = True

    return changed


# =========================================================
# 3. BEST SINGLE-VILLAGE RELOCATION
# =========================================================

def best_relocation(d, instance, routes, loads):

    best_saving = 0
    best_move = None

    for r1 in range(len(routes)):

        route1 = routes[r1]

        # Don't create an empty route.
        if len(route1) <= 1:
            continue

        for i in range(len(route1)):

            village = route1[i]

            previous1 = (
                route1[i - 1]
                if i > 0
                else 0
            )

            next1 = (
                route1[i + 1]
                if i + 1 < len(route1)
                else 0
            )

            # Cost removed from route 1.
            remove_cost = (
                d[previous1][village]
                + d[village][next1]
                - d[previous1][next1]
            )

            demand = instance.demand[village]

            for r2 in range(len(routes)):

                if r1 == r2:
                    continue

                if (
                    loads[r2] + demand
                    > instance.capacity
                ):
                    continue

                route2 = routes[r2]

                for position in range(
                    len(route2) + 1
                ):

                    previous2 = (
                        route2[position - 1]
                        if position > 0
                        else 0
                    )

                    next2 = (
                        route2[position]
                        if position < len(route2)
                        else 0
                    )

                    insert_cost = (
                        d[previous2][village]
                        + d[village][next2]
                        - d[previous2][next2]
                    )

                    saving = (
                        remove_cost
                        - insert_cost
                    )

                    if saving > best_saving:

                        best_saving = saving

                        best_move = (
                            r1,
                            i,
                            r2,
                            position
                        )

    if best_move is None:
        return False

    r1, i, r2, position = best_move

    village = routes[r1].pop(i)

    routes[r2].insert(
        position,
        village
    )

    loads[r1] -= instance.demand[village]
    loads[r2] += instance.demand[village]

    return True


# =========================================================
# 4. BEST SWAP BETWEEN TWO ROUTES
# =========================================================

def best_swap(d, instance, routes, loads):

    best_saving = 0
    best_move = None

    for r1 in range(len(routes)):

        for r2 in range(r1 + 1, len(routes)):

            route1 = routes[r1]
            route2 = routes[r2]

            for i in range(len(route1)):

                village1 = route1[i]

                previous1 = (
                    route1[i - 1]
                    if i > 0
                    else 0
                )

                next1 = (
                    route1[i + 1]
                    if i + 1 < len(route1)
                    else 0
                )

                old1 = (
                    d[previous1][village1]
                    + d[village1][next1]
                )

                for j in range(len(route2)):

                    village2 = route2[j]

                    # Check capacity after swap.
                    new_load1 = (
                        loads[r1]
                        - instance.demand[village1]
                        + instance.demand[village2]
                    )

                    new_load2 = (
                        loads[r2]
                        - instance.demand[village2]
                        + instance.demand[village1]
                    )

                    if new_load1 > instance.capacity:
                        continue

                    if new_load2 > instance.capacity:
                        continue

                    previous2 = (
                        route2[j - 1]
                        if j > 0
                        else 0
                    )

                    next2 = (
                        route2[j + 1]
                        if j + 1 < len(route2)
                        else 0
                    )

                    old2 = (
                        d[previous2][village2]
                        + d[village2][next2]
                    )

                    new1 = (
                        d[previous1][village2]
                        + d[village2][next1]
                    )

                    new2 = (
                        d[previous2][village1]
                        + d[village1][next2]
                    )

                    old_cost = old1 + old2
                    new_cost = new1 + new2

                    saving = (
                        old_cost
                        - new_cost
                    )

                    if saving > best_saving:

                        best_saving = saving

                        best_move = (
                            r1,
                            i,
                            r2,
                            j
                        )

    if best_move is None:
        return False

    r1, i, r2, j = best_move

    village1 = routes[r1][i]
    village2 = routes[r2][j]

    routes[r1][i] = village2
    routes[r2][j] = village1

    loads[r1] = (
        loads[r1]
        - instance.demand[village1]
        + instance.demand[village2]
    )

    loads[r2] = (
        loads[r2]
        - instance.demand[village2]
        + instance.demand[village1]
    )

    return True


# =========================================================
# 5. MAIN SOLVER
# =========================================================

class MySolver(Solver):

    def solve(
        self,
        instance,
        submit_candidate
    ):

        # -------------------------------------------------
        # STEP 1
        # Start with the official starter construction.
        # -------------------------------------------------

        routes = StarterSolver().solve(
            instance,
            submit_candidate
        )["routes"]

        # Precompute all distances.
        d = distance_matrix(instance)

        # Calculate route loads.
        loads = [
            route_load(instance, route)
            for route in routes
        ]

        # -------------------------------------------------
        # STEP 2
        # Submit the initial starter solution immediately.
        # -------------------------------------------------

        receipt = submit_candidate({
            "routes": routes
        })

        # -------------------------------------------------
        # STEP 3
        # Improve each route using 2-opt.
        # -------------------------------------------------

        improve_routes(
            d,
            routes
        )

        receipt = submit_candidate({
            "routes": routes
        })

        # -------------------------------------------------
        # STEP 4
        # Repeatedly improve the whole solution.
        # -------------------------------------------------

        while receipt["remaining_s"] > SAFETY_S:

            improved = False

            # ---------------------------------------------
            # Try moving one village to another route.
            # ---------------------------------------------

            if best_relocation(
                d,
                instance,
                routes,
                loads
            ):

                improved = True

                improve_routes(
                    d,
                    routes
                )

                receipt = submit_candidate({
                    "routes": routes
                })

                continue

            # ---------------------------------------------
            # Try swapping villages between routes.
            # ---------------------------------------------

            if best_swap(
                d,
                instance,
                routes,
                loads
            ):

                improved = True

                improve_routes(
                    d,
                    routes
                )

                receipt = submit_candidate({
                    "routes": routes
                })

                continue

            # ---------------------------------------------
            # Nothing else improved.
            # ---------------------------------------------

            if not improved:
                break

        # -------------------------------------------------
        # STEP 5
        # Remove empty routes.
        # -------------------------------------------------

        routes = [
            route
            for route in routes
            if route
        ]

        # -------------------------------------------------
        # STEP 6
        # Return final solution.
        # -------------------------------------------------

        return {
            "routes": routes
        }
